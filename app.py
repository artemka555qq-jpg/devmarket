from flask import Flask, render_template, request, redirect, url_for, session, abort
from yookassa import Configuration, Payment
import uuid
import os
from dotenv import load_dotenv

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
    "tagline": "Цифровые товары для разработчиков",
    "year": 2026,
    "description": "Готовые боты, шаблоны сайтов, скрипты и гайды. Всё, что нужно для запуска проекта — за пару кликов.",
    "stats": {
        "products": "50+",
        "clients": "1200+",
        "rating": "4.9",
    }
}


@app.context_processor
def inject_brand():
    return {"brand": BRAND}


@app.route("/")
def index():
    products = db.get_all_products()
    return render_template("index.html", products=products)


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

    # Проверка: настроены ли ключи ЮKassa
    if not (SHOP_ID and SECRET_KEY):
        return render_template(
            "success.html",
            error=True,
            message="ЮKassa не настроена. Добавьте SHOP_ID и SECRET_KEY в файл .env"
        )

    try:
        payment = Payment.create({
            "amount": {
                "value": f"{product['price']:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('payment_success', _external=True)
            },
            "capture": True,
            "description": f"Покупка: {product['title']}",
            "metadata": {"product_id": product_id}
        }, uuid.uuid4())

        session['current_payment_id'] = payment.id
        session['current_product_id'] = product_id

        db.create_order(product_id, payment.id)

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