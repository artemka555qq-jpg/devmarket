from flask import Flask, render_template, request, redirect, url_for, session, abort, flash, g
from flask_mail import Mail, Message as MailMessage
from yookassa import Configuration, Payment
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
import os
import time
from datetime import datetime, timedelta
from functools import wraps
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

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2026")
SECRET_ADMIN_URL = "admin-9f8a7b6c"
SECRET_REQUISITES_URL = "requisites-3a7c2d"

# 📁 Загрузка аватаров (без Pillow — просто ограничение по размеру)
AVATAR_FOLDER = "static/avatars"
os.makedirs(AVATAR_FOLDER, exist_ok=True)
ALLOWED_AVATAR_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024  # 3 МБ

# 📧 Mail
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "")

mail = Mail(app)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "support@devmarket.ru")


# 🌍 Переводы
TRANSLATIONS = {
    "ru": {
        "home": "Главная",
        "products": "Товары",
        "cart": "Корзина",
        "blog": "Блог",
        "faq": "FAQ",
        "about": "О нас",
        "contact": "Контакты",
        "login": "Войти",
        "logout": "Выйти",
        "profile": "Профиль",
        "favorites": "Избранное",
        "theme": "Тема",
        "language": "Язык",
        "buy": "Купить сейчас",
        "add_to_cart": "В корзину",
        "checkout": "Оформить заказ",
        "empty_cart": "Корзина пуста",
        "total": "Итого",
        "premium": "Premium",
        "become_premium": "Стать Premium",
        "premium_active": "Premium активен",
        "premium_description": "Расширенные функции и без рекламы",
    },
    "en": {
        "home": "Home",
        "products": "Products",
        "cart": "Cart",
        "blog": "Blog",
        "faq": "FAQ",
        "about": "About",
        "contact": "Contact",
        "login": "Login",
        "logout": "Logout",
        "profile": "Profile",
        "favorites": "Favorites",
        "theme": "Theme",
        "language": "Language",
        "buy": "Buy now",
        "add_to_cart": "Add to cart",
        "checkout": "Checkout",
        "empty_cart": "Cart is empty",
        "total": "Total",
        "premium": "Premium",
        "become_premium": "Become Premium",
        "premium_active": "Premium active",
        "premium_description": "Advanced features and no ads",
    }
}


BRAND = {
    "name": "DevMarket",
    "tagline": "Готовые решения для разработчиков",
    "tagline_en": "Ready-made solutions for developers",
    "year": 2026,
    "description": "Цифровые товары, которые работают с первого запуска. Боты, сайты, скрипты и гайды — всё для вашего проекта.",
    "description_en": "Digital products that work from the first launch. Bots, sites, scripts and guides — everything for your project.",
    "contacts": {
        "telegram": "@devmarket_support",
        "email": "support@devmarket.ru",
    },
    "premium_price": 499,
}

ALLOWED_YOO_IPS = ('185.71.76.', '185.71.77.', '185.71.78.', '185.71.79.', '77.75.153.', '77.75.154.', '77.75.156.')


def get_lang():
    """Возвращает текущий язык."""
    return session.get("lang", "ru")


def t(key):
    """Перевод по ключу."""
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS["ru"]).get(key, key)


@app.context_processor
def inject_globals():
    user = get_current_user()
    cart_count = db.get_cart_count(user["id"]) if user else 0
    return {
        "brand": BRAND,
        "current_user": user,
        "cart_count": cart_count,
        "t": t,
        "lang": get_lang(),
    }


def get_current_user():
    if session.get("user_id"):
        return db.get_user_by_id(session["user_id"])
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Войдите в аккаунт" if get_lang() == "ru" else "Please log in", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def allowed_avatar(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXT


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


# ---------- Язык и тема ----------
@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ["ru", "en"]:
        session["lang"] = lang
        if session.get("user_id"):
            db.update_user(session["user_id"], language=lang)
    return redirect(request.referrer or url_for("index"))


@app.route("/set-theme/<theme>")
def set_theme(theme):
    if theme in ["dark", "light"]:
        session["theme"] = theme
        if session.get("user_id"):
            db.update_user(session["user_id"], theme=theme)
    return redirect(request.referrer or url_for("index"))


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


@app.route("/blog")
def blog():
    posts = db.get_all_posts()
    return render_template("blog.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = db.get_post_by_slug(slug)
    if not post:
        abort(404)
    return render_template("blog_post.html", post=post)


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
    in_cart = False
    if session.get("user_id"):
        is_fav = db.is_favorite(session["user_id"], product_id)
        cart = db.get_cart(session["user_id"])
        in_cart = any(item["id"] == product_id for item in cart)

    return render_template(
        "product.html",
        product=product,
        reviews=reviews,
        avg_rating=avg_rating,
        reviews_count=reviews_count,
        similar=similar,
        is_fav=is_fav,
        in_cart=in_cart,
    )


@app.route("/product/<int:product_id>/review", methods=["POST"])
def add_review(product_id):
    if not session.get("user_id"):
        flash("Войдите, чтобы оставить отзыв" if get_lang() == "ru" else "Please log in", "error")
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
        flash("Оценка 1–5" if get_lang() == "ru" else "Rating 1–5", "error")
    elif not text:
        flash("Напишите отзыв" if get_lang() == "ru" else "Write a review", "error")
    else:
        db.add_review(product_id, session["username"], rating, text)
        flash("Спасибо за отзыв!" if get_lang() == "ru" else "Thanks for your review!", "success")

    return redirect(url_for("product_detail", product_id=product_id))


@app.route("/product/<int:product_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(product_id):
    added = db.toggle_favorite(session["user_id"], product_id)
    flash("Добавлено в избранное ⭐" if added else "Удалено из избранного", "success")
    return redirect(url_for("product_detail", product_id=product_id))


# ---------- Корзина ----------
@app.route("/cart")
@login_required
def cart():
    items = db.get_cart(session["user_id"])
    total = sum(item["price"] * item["quantity"] for item in items)
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)
    db.add_to_cart(session["user_id"], product_id)
    flash(f"«{product['title']}» добавлен в корзину" if get_lang() == "ru" else "Added to cart", "success")
    return redirect(request.referrer or url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def cart_remove(product_id):
    db.remove_from_cart(session["user_id"], product_id)
    flash("Удалено из корзины" if get_lang() == "ru" else "Removed", "success")
    return redirect(url_for("cart"))


@app.route("/cart/checkout", methods=["POST"])
@login_required
def cart_checkout():
    items = db.get_cart(session["user_id"])
    if not items:
        flash("Корзина пуста" if get_lang() == "ru" else "Cart is empty", "error")
        return redirect(url_for("cart"))

    buyer_email = request.form.get("buyer_email", "").strip()
    promo_code = request.form.get("promo_code", "").strip().upper()

    if not buyer_email:
        flash("Укажите email" if get_lang() == "ru" else "Enter your email", "error")
        return redirect(url_for("cart"))

    total = sum(item["price"] * item["quantity"] for item in items)

    applied_promo = None
    if promo_code:
        promo = db.get_promocode(promo_code)
        if promo:
            total = total * (100 - promo["discount"]) / 100
            applied_promo = promo_code
        else:
            flash(f"Промокод {promo_code} не найден" if get_lang() == "ru" else "Promo not found", "error")
            return redirect(url_for("cart"))

    if not (SHOP_ID and SECRET_KEY):
        flash("ЮKassa не настроена", "error")
        return redirect(url_for("cart"))

    try:
        # Собираем описание заказа
        titles = ", ".join([item["title"] for item in items])[:128]

        payment = Payment.create({
            "amount": {"value": f"{total:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('payment_success', _external=True)
            },
            "capture": True,
            "description": f"Заказ: {titles}",
            "metadata": {
                "cart": "true",
                "buyer_email": buyer_email,
                "promo_code": applied_promo or "",
                "final_price": total
            }
        }, uuid.uuid4())

        # Создаём заказ для каждого товара
        for item in items:
            db.create_order(
                item["id"], f"{payment.id}_{item['id']}", "pending",
                buyer_email, applied_promo, item["price"],
                session.get("user_id")
            )

        session['current_payment_id'] = payment.id
        session['current_product_id'] = items[0]["id"]

        if applied_promo:
            db.use_promocode(applied_promo)

        db.clear_cart(session["user_id"])

        return redirect(payment.confirmation.confirmation_url)

    except Exception as e:
        print(f"Ошибка: {e}")
        flash(f"Ошибка: {e}", "error")
        return redirect(url_for("cart"))


# ---------- Premium ----------
@app.route("/premium")
def premium():
    return render_template("premium.html", price=BRAND["premium_price"])


@app.route("/premium/buy", methods=["POST"])
@login_required
def premium_buy():
    if not (SHOP_ID and SECRET_KEY):
        flash("ЮKassa не настроена", "error")
        return redirect(url_for("premium"))

    try:
        payment = Payment.create({
            "amount": {"value": f"{BRAND['premium_price']:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": url_for('payment_success', _external=True)
            },
            "capture": True,
            "description": "Premium подписка на 1 месяц",
            "metadata": {
                "premium": "true",
                "user_id": session["user_id"],
                "buyer_email": request.form.get("buyer_email", ""),
                "final_price": BRAND["premium_price"]
            }
        }, uuid.uuid4())

        session['current_payment_id'] = payment.id
        session['premium_payment'] = True

        return redirect(payment.confirmation.confirmation_url)

    except Exception as e:
        flash(f"Ошибка: {e}", "error")
        return redirect(url_for("premium"))


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
            flash("Регистрация успешна!" if get_lang() == "ru" else "Registration successful!", "success")
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
            if user["language"]:
                session["lang"] = user["language"]
            if user["theme"]:
                session["theme"] = user["theme"]
            flash(f"Добро пожаловать, {user['username']}!", "success")
            return redirect(url_for("index"))
        flash("Неверный логин или пароль" if get_lang() == "ru" else "Wrong login or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли" if get_lang() == "ru" else "Logged out", "success")
    return redirect(url_for("index"))


# ---------- Личный кабинет ----------
@app.route("/profile")
@login_required
def profile():
    user = db.get_user_by_id(session["user_id"])
    orders = db.get_user_orders(session["user_id"])
    favorites = db.get_user_favorites(session["user_id"])
    return render_template("profile.html", user=user, orders=orders, favorites=favorites)


@app.route("/profile/avatar", methods=["POST"])
@login_required
def change_avatar():
    file = request.files.get("avatar")
    if not file or not file.filename:
        flash("Выберите файл" if get_lang() == "ru" else "Select a file", "error")
        return redirect(url_for("profile"))

    if not allowed_avatar(file.filename):
        flash("Допустимы PNG, JPG, JPEG, GIF, WEBP", "error")
        return redirect(url_for("profile"))

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"user_{session['user_id']}_{int(time.time())}.{ext}"
    filepath = os.path.join(AVATAR_FOLDER, filename)

    # Удаляем старый аватар
    old_user = db.get_user_by_id(session["user_id"])
    if old_user["avatar"]:
        old_path = os.path.join(AVATAR_FOLDER, old_user["avatar"])
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    file.save(filepath)
    db.update_user(session["user_id"], avatar=filename)
    flash("Аватар обновлён" if get_lang() == "ru" else "Avatar updated", "success")
    return redirect(url_for("profile"))


@app.route("/profile/email", methods=["POST"])
@login_required
def change_email():
    new_email = request.form.get("email", "").strip().lower()
    if not new_email or "@" not in new_email:
        flash("Некорректный email", "error")
    elif db.get_user_by_email(new_email):
        flash("Email занят", "error")
    else:
        db.update_user(session["user_id"], email=new_email)
        flash("Email обновлён" if get_lang() == "ru" else "Email updated", "success")
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
        flash("Пароль обновлён" if get_lang() == "ru" else "Password updated", "success")
    return redirect(url_for("profile"))


@app.route("/profile/username", methods=["POST"])
@login_required
def change_username():
    new_username = request.form.get("username", "").strip()
    if len(new_username) < 3:
        flash("Логин не короче 3 символов", "error")
    elif db.get_user_by_username(new_username):
        flash("Логин занят", "error")
    else:
        db.update_user(session["user_id"], username=new_username)
        session["username"] = new_username
        flash("Логин обновлён" if get_lang() == "ru" else "Username updated", "success")
    return redirect(url_for("profile"))


@app.route("/favorites")
@login_required
def favorites():
    items = db.get_user_favorites(session["user_id"])
    return render_template("favorites.html", products=items)


# ---------- Оплата (для отдельного товара) ----------
@app.route("/create_payment/<int:product_id>", methods=["POST"])
def create_payment(product_id):
    product = db.get_product(product_id)
    if not product:
        abort(404)

    if not (SHOP_ID and SECRET_KEY):
        return render_template("success.html", error=True, message="ЮKassa не настроена")

    promo_code = request.form.get("promo_code", "").strip().upper()
    buyer_email = request.form.get("buyer_email", "").strip()

    final_price = product["price"]
    applied_promo = None

    if promo_code:
        promo = db.get_promocode(promo_code)
        if promo:
            final_price = product["price"] * (100 - promo["discount"]) / 100
            applied_promo = promo_code
        else:
            flash("Промокод не найден", "error")
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
    is_premium = session.pop("premium_payment", False)
    return render_template("success.html", product=product, error=False, is_premium=is_premium)


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
        is_premium = metadata.get("premium") == "true"
        is_cart = metadata.get("cart") == "true"

        # Premium
        if is_premium:
            user_id = metadata.get("user_id")
            if user_id:
                until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
                db.update_user(int(user_id), is_premium=1, premium_until=until)
            send_email(ADMIN_EMAIL, "💰 Premium подписка", f"Пользователь ID {metadata.get('user_id')} купил Premium")
            print(f"✅ Premium куплен")
        # Корзина
        elif is_cart:
            # Обновляем все заказы с этим payment_id
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE orders SET status = 'paid' WHERE payment_id LIKE ?",
                    (f"{payment_id}%",)
                )
                conn.commit()
            send_email(ADMIN_EMAIL, "💰 Новый заказ (корзина)", f"Payment ID: {payment_id}")
            print(f"✅ Корзина оплачена")
        # Обычная покупка
        else:
            db.mark_order_paid(payment_id)
            product_id = metadata.get("product_id")
            product = db.get_product(int(product_id)) if product_id else None
            title = product["title"] if product else "товар"
            send_email(ADMIN_EMAIL, f"💰 Новый заказ: {title}", f"Payment ID: {payment_id}")
            if buyer_email and product:
                send_email(
                    buyer_email,
                    "Спасибо за покупку в DevMarket!",
                    f"Спасибо за покупку «{title}»!\nСсылка: {product['download_url']}"
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
            title_en = request.form.get("title_en", "").strip()
            description = request.form.get("description", "").strip()
            description_en = request.form.get("description_en", "").strip()
            price = float(request.form.get("price", "0"))
            image_url = request.form.get("image_url", "").strip()
            download_url = request.form.get("download_url", "").strip()
            category = request.form.get("category", "Прочее").strip()
            badge = request.form.get("badge", "").strip() or None

            if not (title and price > 0 and download_url):
                flash("Заполните обязательные поля", "error")
            else:
                db.add_product(title, title_en, description, description_en, price, image_url, download_url, category, badge)
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

    # Блог
    if request.method == "POST" and "post_title" in request.form:
        title = request.form.get("post_title", "").strip()
        slug = request.form.get("post_slug", "").strip().lower().replace(" ", "-")
        excerpt = request.form.get("post_excerpt", "").strip()
        content = request.form.get("post_content", "").strip()
        image_url = request.form.get("post_image", "").strip()

        if not (title and slug and content):
            flash("Заполните заголовок, slug и текст", "error")
        else:
            db.add_post(title, slug, excerpt, content, image_url)
            flash(f"Статья «{title}» добавлена", "success")
            return redirect(url_for("admin"))

    products = db.get_all_products()
    orders = db.get_all_orders()
    promocodes = db.get_all_promocodes()
    stats = db.get_orders_stats()
    posts = db.get_all_posts()
    return render_template("admin.html", products=products, orders=orders, promocodes=promocodes, stats=stats, posts=posts)


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
            title_en = request.form.get("title_en", "").strip()
            description = request.form.get("description", "").strip()
            description_en = request.form.get("description_en", "").strip()
            price = float(request.form.get("price", "0"))
            image_url = request.form.get("image_url", "").strip()
            download_url = request.form.get("download_url", "").strip()
            category = request.form.get("category", "Прочее").strip()
            badge = request.form.get("badge", "").strip() or None

            if not (title and price > 0 and download_url):
                flash("Заполните обязательные поля", "error")
            else:
                db.update_product(product_id, title, title_en, description, description_en, price, image_url, download_url, category, badge)
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


@app.route(f"/{SECRET_ADMIN_URL}/post/delete/<int:post_id>", methods=["POST"])
def admin_delete_post(post_id):
    if not session.get("is_admin"):
        abort(403)
    db.delete_post(post_id)
    flash("Статья удалена", "success")
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