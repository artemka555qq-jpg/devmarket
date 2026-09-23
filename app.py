from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from yookassa import Configuration, Payment
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
from dotenv import load_dotenv

import database as db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

if SHOP_ID and SECRET_KEY:
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = SECRET_KEY

# 🔐 Пароль для админки
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2026")


# 🎨 Бренд
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

ALLOWED_YOO_IPS = ('185.71.76.', '185.71.77.', '185.71.78.', '185.71.79.', '77.75.153.', '77.75.154.', '77.75.156.')


@app.context_processor
def inject_brand():
    return {"brand": BRAND}


# ---------- Публичные страницы ----------
@app.route("/")
def index():
    products = db.get_all_products()
    return render_template("index.html", products=products)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if query:
        products = db.search_products(query)
    else:
        products = db.get_all_products()
    return render_template("search.html", products=products, query=query)


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


# ---------- Регистрация и вход ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (username and email and password):
            flash("Заполните все поля", "error")
        elif len(username) < 3:
            flash("Логин должен быть не короче 3 символов", "error")
        elif len(password) < 6:
            flash("Пароль должен быть не короче 6 символов", "error")
        elif db.get_user_by_username(username):
            flash("Такой логин уже занят", "error")
        elif db.get_user_by_email(email):
            flash("Такой email уже занят", "error")
        else:
            db.create_user(username, email, generate_password_hash(password))
            flash("Регистрация успешна! Войдите.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Добро пожаловать, {user['username']}!", "success")
            return redirect(url_for("index"))

        flash("Неверный логин или пароль", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли", "success")
    return redirect(url_for("index"))


# ---------- Оплата ----------
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
        payment = Payment.create({
            "amount": {"value": f"{product['price']:.2f}", "currency": "RUB"},
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
        return render_template("success.html", error=True, message=f"Не удалось создать платёж: {e}")


@app.route("/payment_success")
def payment_success():
    product_id = session.get('current_product_id')
    product = db.get_product(product_id) if product_id else None
    return render_template("success.html", product=product, error=False)


@app.route("/webhook/yookassa", methods=["POST"])
def yookassa_webhook():
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


# ---------- Админ-панель ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "password" in request.form:
        if request.form["password"] == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("Неверный пароль", "error")

    if not session.get("is_admin"):
        return render_template("admin_login.html")

    if request.method == "POST" and "title" in request.form:
        try:
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            price = float(request.form.get("price", "0"))
            image_url = request.form.get("image_url", "").strip()
            download_url = request.form.get("download_url", "").strip()
            category = request.form.get("category", "Прочее").strip()
            badge = request.form.get("badge", "").strip() or None

            if not (title and price > 0 and download_url):
                flash("Заполните обязательные поля", "error")
            else:
                db.add_product(title, description, price, image_url, download_url, category, badge)
                flash(f"Товар «{title}» добавлен", "success")
                return redirect(url_for("admin"))
        except ValueError:
            flash("Неверная цена", "error")

    products = db.get_all_products()
    orders = db.get_all_orders()
    return render_template("admin.html", products=products, orders=orders)


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
def admin_delete(product_id):
    if not session.get("is_admin"):
        abort(403)
    db.delete_product(product_id)
    flash("Товар удалён", "success")
    return redirect(url_for("admin"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Вы вышли из админки", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", error_404=True), 404


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5000)