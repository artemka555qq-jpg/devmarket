from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from flask_mail import Mail, Message as MailMessage
from yookassa import Configuration, Payment
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
from dotenv import load_dotenv
from functools import wraps

import database as db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

if SHOP_ID and SECRET_KEY:
    Configuration.account_id = SHOP_ID
    Configuration.secret_key = SECRET_KEY

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2026")
SECRET_ADMIN_URL = "admin-9f8a7b6c"
SECRET_REQUISITES_URL = "requisites-3a7c2d"

# 📧 Mail
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "")

mail = Mail(app)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "support@devmarket.ru")


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
    return {"brand": BRAND, "current_user": get_current_user()}


def get_current_user():
    """Возвращает текущего пользователя или None."""
    if session.get("user_id"):
        return db.get_user_by_id(session["user_id"])
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Войдите в аккаунт", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def send_email(to, subject, body):
    if not app.config["MAIL_USERNAME"]:
        print(f"📧 [email skipped] To: {to}, Subject: {subject}")
        return
    try:
        msg = MailMessage(subject=subject, recipients=[to], body=body)
        mail.send(msg)
        print(f"📧 Email sent to {to}")
    except Exception as e:
        print(f"❌ Email error: {e}")


# ---------- Публичные страницы ----------
@app.route("/")
def index():
    products = db.get_all_products()
    return render_template("index.html", products=products)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    products = db.search_products(query) if query else db.get_all_products()
    return render_template("search.html", products=products, query=query)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faq")
def faq():
    items = db.get_all_faq()
    return render_template("faq.html", items=items)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        return render_template("contact.html", success=True)
    return render_template("contact.html", success=False)


@app.route(f"/{SECRET_REQUISITES_URL}")
def requisites():
    return render_template("requisites.html")


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)

    reviews = db.get_reviews(product_id)
    avg_rating, reviews_count = db.get_avg_rating(product_id)
    similar = db.get_similar_products(product_id, product["category"], limit=3)

    is_fav = False
    if session.get("user_id"):
        is_fav = db.is_favorite(session["user_id"], product_id)

    return render_template(
        "product.html",
        product=product,
        reviews=reviews,
        avg_rating=avg_rating,
        reviews_count=reviews_count,
        similar=similar,
        is_fav=is_fav
    )


@app.route("/product/<int:product_id>/review", methods=["POST"])
def add_review(product_id):
    if not session.get("user_id"):
        flash("Войдите, чтобы оставить отзыв", "error")
        return redirect(url_for("login"))

    product = db.get_product(product_id)
    if not product:
        abort(404)

    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0

    text = request.form.get("text", "").strip()

    if rating < 1 or rating > 5:
        flash("Оценка должна быть от 1 до 5", "error")
    elif not text:
        flash("Напишите текст отзыва", "error")
    else:
        db.add_review(product_id, session["username"], rating, text)
        flash("Спасибо за отзыв!", "success")

    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/product/<int:product_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(product_id):
    added = db.toggle_favorite(session["user_id"], product_id)
    flash("Добавлено в избранное ⭐" if added else "Удалено из избранного", "success")
    return redirect(url_for("product_detail", product_id=product_id))


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
            flash("Логин не короче 3 символов", "error")
        elif len(password) < 6:
            flash("Пароль не короче 6 символов", "error")
        elif db.get_user_by_username(username):
            flash("Логин занят", "error")
        elif db.get_user_by_email(email):
            flash("Email занят", "error")
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


# ---------- Личный кабинет ----------
@app.route("/profile")
@login_required
def profile():
    user = db.get_user_by_id(session["user_id"])
    orders = db.get_user_orders(session["user_id"])
    favorites = db.get_user_favorites(session["user_id"])
    return render_template("profile.html", user=user, orders=orders, favorites=favorites)


@app.route("/profile/email", methods=["POST"])
@login_required
def change_email():
    new_email = request.form.get("email", "").strip().lower()
    if not new_email or "@" not in new_email:
        flash("Некорректный email", "error")
    elif new_email == session.get("email"):
        flash("Это ваш текущий email", "error")
    elif db.get_user_by_email(new_email):
        flash("Email уже занят", "error")
    else:
        db.update_user(session["user_id"], email=new_email)
        flash("Email обновлён", "success")
    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    old = request.form.get("old_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    user = db.get_user_by_id(session["user_id"])
    if not check_password_hash(user["password_hash"], old):
        flash("Старый пароль неверный", "error")
    elif len(new) < 6:
        flash("Новый пароль не короче 6 символов", "error")
    elif new != confirm:
        flash("Пароли не совпадают", "error")
    else:
        db.update_user(session["user_id"], password_hash=generate_password_hash(new))
        flash("Пароль обновлён", "success")
    return redirect(url_for("profile"))


@app.route("/profile/username", methods=["POST"])
@login_required
def change_username():
    new_username = request.form.get("username", "").strip()
    if len(new_username) < 3:
        flash("Логин не короче 3 символов", "error")
    elif new_username == session.get("username"):
        flash("Это ваш текущий логин", "error")
    elif db.get_user_by_username(new_username):
        flash("Логин занят", "error")
    else:
        db.update_user(session["user_id"], username=new_username)
        session["username"] = new_username
        flash("Логин обновлён", "success")
    return redirect(url_for("profile"))


@app.route("/favorites")
@login_required
def favorites():
    items = db.get_user_favorites(session["user_id"])
    return render_template("favorites.html", products=items)


# ---------- Оплата ----------
@app.route("/create_payment/<int:product_id>", methods=["POST"])
def create_payment(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)

    if not (SHOP_ID and SECRET_KEY):
        return render_template("success.html", error=True, message="ЮKassa не настроена.")

    promo_code = request.form.get("promo_code", "").strip().upper()
    buyer_email = request.form.get("buyer_email", "").strip()

    final_price = product["price"]
    applied_promo = None

    if promo_code:
        promo = db.get_promocode(promo_code)
        if promo:
            final_price = product["price"] * (100 - promo["discount"]) / 100
            applied_promo = promo_code
            flash(f"Промокод {promo_code}: скидка {promo['discount']}%", "success")
        else:
            flash(f"Промокод не найден", "error")
            return redirect(url_for("product_detail", product_id=product_id))

    try:
        payment = Payment.create({
            "amount": {"value": f"{final_price:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('payment_success', _external=True)
            },
            "capture": True,
            "description": f"Покупка: {product['title']}",
            "metadata": {
                "product_id": product_id,
                "buyer_email": buyer_email,
                "promo_code": applied_promo or "",
                "final_price": final_price
            }
        }, uuid.uuid4())

        session['current_payment_id'] = payment.id
        session['current_product_id'] = product_id

        db.create_order(
            product_id, payment.id, "pending",
            buyer_email, applied_promo, final_price,
            session.get("user_id")
        )

        if applied_promo:
            db.use_promocode(applied_promo)

        return redirect(payment.confirmation.confirmation_url)

    except Exception as e:
        print(f"Ошибка: {e}")
        return render_template("success.html", error=True, message=f"Ошибка: {e}")


@app.route("/payment_success")
def payment_success():
    product_id = session.get('current_product_id')
    product = db.get_product(product_id) if product_id else None
    return render_template("success.html", product=product, error=False)


@app.route("/webhook/yookassa", methods=["POST"])
def yookassa_webhook():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    if not any(client_ip.startswith(prefix) for prefix in ALLOWED_YOO_IPS):
        abort(403)

    data = request.json
    if data.get("event") == "payment.succeeded":
        payment_obj = data.get("object", {})
        payment_id = payment_obj.get("id")
        metadata = payment_obj.get("metadata", {})
        buyer_email = metadata.get("buyer_email", "")
        product_id = metadata.get("product_id")

        db.mark_order_paid(payment_id)

        product = db.get_product(int(product_id)) if product_id else None
        title = product["title"] if product else "товар"
        send_email(
            ADMIN_EMAIL,
            f"💰 Новый заказ: {title}",
            f"Товар: {title}\nPayment ID: {payment_id}\nEmail: {buyer_email or 'не указан'}"
        )
        if buyer_email:
            send_email(
                buyer_email,
                "Спасибо за покупку в DevMarket!",
                f"Спасибо за покупку «{title}»!\nСсылка: {product['download_url'] if product else ''}"
            )
        print(f"✅ Платёж {payment_id} оплачен")

    return "OK", 200


# ---------- Админка ----------
@app.route(f"/{SECRET_ADMIN_URL}", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "password" in request.form:
        if request.form["password"] == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("Неверный пароль", "error")

    if not session.get("is_admin"):
        return render_template("admin_login.html")

    # Добавить товар
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

    # Промокод
    if request.method == "POST" and "promo_code" in request.form:
        code = request.form.get("promo_code", "").strip().upper()
        try:
            discount = int(request.form.get("discount", "0"))
            uses = int(request.form.get("uses", "100"))
        except ValueError:
            discount, uses = 0, 100

        if not code or discount < 1 or discount > 99:
            flash("Промокод и скидка 1–99%", "error")
        else:
            db.add_promocode(code, discount, uses)
            flash(f"Промокод {code} добавлен", "success")
            return redirect(url_for("admin"))

    products = db.get_all_products()
    orders = db.get_all_orders()
    promocodes = db.get_all_promocodes()
    stats = db.get_orders_stats()
    return render_template("admin.html", products=products, orders=orders, promocodes=promocodes, stats=stats)


@app.route(f"/{SECRET_ADMIN_URL}/edit/<int:product_id>", methods=["GET", "POST"])
def admin_edit(product_id):
    if not session.get("is_admin"):
        abort(403)

    product = db.get_product(product_id)
    if not product:
        abort(404)

    if request.method == "POST":
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
                db.update_product(product_id, title, description, price, image_url, download_url, category, badge)
                flash("Товар обновлён", "success")
                return redirect(url_for("admin"))
        except ValueError:
            flash("Неверная цена", "error")

    return render_template("admin_edit.html", product=product)


@app.route(f"/{SECRET_ADMIN_URL}/delete/<int:product_id>", methods=["POST"])
def admin_delete(product_id):
    if not session.get("is_admin"):
        abort(403)
    db.delete_product(product_id)
    flash("Товар удалён", "success")
    return redirect(url_for("admin"))


@app.route(f"/{SECRET_ADMIN_URL}/promo/delete/<code>", methods=["POST"])
def admin_delete_promo(code):
    if not session.get("is_admin"):
        abort(403)
    db.delete_promocode(code)
    flash(f"Промокод {code} удалён", "success")
    return redirect(url_for("admin"))


@app.route(f"/{SECRET_ADMIN_URL}/logout")
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