from flask import Flask, render_template, request, redirect, url_for, session, abort
from yookassa import Configuration, Payment
import uuid
import os
from dotenv import load_dotenv
import sqlite3 # Для проверки IP вебхука

import database as db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

# Настраиваем ЮKassa (если ключи указаны)
if SHOP_ID and SECRET_KEY:
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = SECRET_KEY

# 🎨 Информация о бренде
BRAND = {
    "name": "DevMarket",
    "tagline": "Готовые решения для разработчиков",
    "year": 2026,
    "description": "Цифровые товары, которые работают с первого запуска. Боты, сайты, скрипты и гайды — всё для вашего проекта.",
    "contacts": {
        "telegram": "@devmarket_support",
        "email": "support@devmarket.ru",
    },
}

# Разрешённые IP-адреса ЮKassa для проверки вебхуков
ALLOWED_YOO_IPS = ('185.71.76.', '185.71.77.', '185.71.78.', '185.71.79.', '77.75.153.', '77.75.154.', '77.75.156.')

@app.context_processor
def inject_brand():
    return {"brand": BRAND}

@app.route("/")
def index():
    products = db.get_all_products()
    return render_template("index.html", products=products)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        return render_template("contact.html", success=True)
    return render_template("contact.html", success=False)

@app.route("/requisites")
def requisites():
    return render_template("requisites.html")

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)
    return render_template("product.html", product=product)

@app.route("/create_payment/<int:product_id>", methods=["POST"])
def create_payment(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)

    if not (SHOP_ID and SECRET_KEY):
        return render_template(
            "success.html",
            error=True,
            message="ЮKassa не настроена. Добавьте SHOP_ID и SECRET_KEY в файл .env"
        )

    try:
        # Создаём платёж в ЮKassa
        payment = Payment.create({
            "amount": {
                "value": f"{product['price']:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('payment_success', _external=True)
            },
            "capture": True,  # Одностадийная оплата (сразу списываем)
            "description": f"Покупка: {product['title']}",
            "metadata": {"product_id": product_id}
        }, uuid.uuid4())  # Ключ идемпотентности [citation:1][citation:7]

        # Сохраняем ID платежа в сессии и БД
        session['current_payment_id'] = payment.id
        session['current_product_id'] = product_id
        db.create_order(product_id, payment.id)

        # Перенаправляем на страницу оплаты ЮKassa [citation:7][citation:8]
        return redirect(payment.confirmation.confirmation_url)

    except Exception as e:
        print(f"Ошибка создания платежа: {e}")
        return render_template(
            "success.html",
            error=True,
            message=f"Не удалось создать платёж: {e}"
        )

@app.route("/payment_success")
def payment_success():
    product_id = session.get('current_product_id')
    product = db.get_product(product_id) if product_id else None
    return render_template("success.html", product=product, error=False)

@app.route("/webhook/yookassa", methods=["POST"])
def yookassa_webhook():
    """Сюда ЮKassa присылает уведомления о статусе платежа."""
    # 1. Проверка IP-адреса отправителя (защита от подделок) [citation:4][citation:15]
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not any(client_ip.startswith(prefix) for prefix in ALLOWED_YOO_IPS):
        print(f"🚨 Попытка несанкционированного доступа с IP: {client_ip}")
        abort(403)

    data = request.json
    event = data.get("event")

    if event == "payment.succeeded":
        payment_obj = data.get("object", {})
        payment_id = payment_obj.get("id")
        db.mark_order_paid(payment_id)
        print(f"✅ Платёж {payment_id} оплачен")

    return "OK", 200

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", error_404=True), 404

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5000)