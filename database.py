import sqlite3
from datetime import datetime

DB_PATH = "devmarket.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_en TEXT,
                description TEXT,
                description_en TEXT,
                price REAL NOT NULL,
                image_url TEXT,
                download_url TEXT,
                category TEXT DEFAULT 'Прочее',
                badge TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                user_id INTEGER,
                payment_id TEXT UNIQUE,
                status TEXT,
                buyer_email TEXT,
                promo_code TEXT,
                final_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                language TEXT DEFAULT 'ru',
                theme TEXT DEFAULT 'dark',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                rating INTEGER NOT NULL,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount INTEGER NOT NULL,
                uses_left INTEGER DEFAULT 100,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id)
            );

            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id)
            );

            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                question_en TEXT,
                answer_en TEXT,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS blog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                excerpt TEXT,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur = conn.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            products = [
                (
                    "Шаблон Telegram-бота PlayWatch",
                    "PlayWatch Telegram Bot Template",
                    "Готовый Telegram-бот на Python: погода, курсы крипты, игры, цитаты и шутки. Запуск за 5 минут.",
                    "Ready-to-use Telegram bot on Python: weather, crypto rates, games, quotes and jokes. Launch in 5 minutes.",
                    499.00,
                    "https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?w=900",
                    "https://drive.google.com/uc?export=download&id=1HLlCFcHwPvs3dEgMD1H6BN4bmiPtM_gS",
                    "Боты",
                    "ХИТ"
                ),
                (
                    "100 промптов для ChatGPT 2026",
                    "100 ChatGPT Prompts 2026",
                    "Сборник из 100+ проверенных промптов для маркетинга, кода, текстов и бизнеса.",
                    "Collection of 100+ proven prompts for marketing, coding, texts and business.",
                    349.00,
                    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=900",
                    "https://drive.google.com/uc?export=download&id=1Pcbb7S8HaHPN-MR66mIEZ8QIrp_ikQhA",
                    "Гайды",
                    "TOP"
                ),
                (
                    "Гайд: деплой бота и сайта на Render",
                    "Guide: Deploy Bot and Site on Render",
                    "PDF-инструкция на 25 страниц: как залить проект на GitHub и поднять на Render.",
                    "PDF guide on 25 pages: how to upload a project to GitHub and deploy on Render.",
                    199.00,
                    "https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?w=900",
                    "https://drive.google.com/uc?export=download&id=1ATcUqgFxsA39-sSe1Y3_pcYC4dBFTSfI",
                    "Гайды",
                    None
                ),
            ]
            for p in products:
                conn.execute(
                    """INSERT INTO products
                       (title, title_en, description, description_en, price, image_url, download_url, category, badge)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    p
                )

            conn.execute("INSERT INTO promocodes (code, discount, uses_left) VALUES (?, ?, ?)", ("WELCOME10", 10, 999))
            conn.execute("INSERT INTO promocodes (code, discount, uses_left) VALUES (?, ?, ?)", ("DEVMARKET20", 20, 100))

            faq_items = [
                ("Как я получу товар после оплаты?",
                 "Сразу после оплаты вы получите ссылку на скачивание на email. Ссылка также появится в личном кабинете.",
                 "How will I get the product after payment?",
                 "Right after payment you will receive a download link by email. The link will also appear in your account.",
                 1),
                ("Можно ли вернуть деньги?",
                 "Да, в течение 14 дней после покупки. Напишите на support@devmarket.ru — оформим возврат.",
                 "Can I get a refund?",
                 "Yes, within 14 days after purchase. Email support@devmarket.ru — we will process the refund.",
                 2),
                ("Можно ли использовать шаблоны в коммерческих целях?",
                 "Да, все товары можно использовать в личных и коммерческих проектах.",
                 "Can I use templates commercially?",
                 "Yes, all products can be used in personal and commercial projects.",
                 3),
                ("Как применить промокод?",
                 "Введите промокод в поле «Промокод» на странице товара или в корзине.",
                 "How do I apply a promo code?",
                 "Enter the promo code in the «Promo Code» field on the product page or in the cart.",
                 4),
            ]
            for q in faq_items:
                conn.execute("INSERT INTO faq (question, answer, question_en, answer_en, sort_order) VALUES (?, ?, ?, ?, ?)", q)

            blog_items = [
                (
                    "Как задеплоить Telegram-бота на Render за 30 минут",
                    "deploy-telegram-bot-render",
                    "Пошаговая инструкция по деплою бота на бесплатный хостинг Render.",
                    "Render — это облачный хостинг, который позволяет развернуть Telegram-бота бесплатно. В этой статье разберём все шаги: от подготовки кода до запуска бота 24/7.\n\n## Шаг 1. Подготовка проекта\n\nСоздайте файл requirements.txt со списком зависимостей...\n\n## Шаг 2. Загрузка на GitHub\n\nСоздайте репозиторий на github.com/new...\n\n## Шаг 3. Деплой на Render\n\nЗарегистрируйтесь на render.com и создайте Web Service...",
                    "https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?w=900"
                ),
                (
                    "5 идей для заработка на Telegram-ботах в 2026",
                    "earn-on-telegram-bots-2026",
                    "Как заработать на создании Telegram-ботов в 2026 году.",
                    "Telegram-боты — это один из самых перспективных способов заработка в 2026 году. Вот 5 идей, которые работают прямо сейчас.\n\n## 1. Боты для бизнеса\n\nКаждый магазин, салон, кафе нуждается в боте для приёма заказов...\n\n## 2. AI-ассистенты\n\nС интеграцией OpenAI можно создавать умных консультантов...",
                    "https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?w=900"
                ),
            ]
            for b in blog_items:
                conn.execute("INSERT INTO blog (title, slug, excerpt, content, image_url) VALUES (?, ?, ?, ?, ?)", b)

            conn.commit()


# ---------- Товары ----------
def get_all_products():
    with get_db() as conn:
        return conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()


def get_product(product_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def search_products(query):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE title LIKE ? OR title_en LIKE ? OR description LIKE ? ORDER BY id DESC",
            (f"%{query}%", f"%{query}%", f"%{query}%")
        ).fetchall()


def add_product(title, title_en, description, description_en, price, image_url, download_url, category, badge):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO products
               (title, title_en, description, description_en, price, image_url, download_url, category, badge)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, title_en, description, description_en, price, image_url, download_url, category, badge)
        )
        conn.commit()


def update_product(product_id, title, title_en, description, description_en, price, image_url, download_url, category, badge):
    with get_db() as conn:
        conn.execute(
            """UPDATE products SET
                title = ?, title_en = ?, description = ?, description_en = ?,
                price = ?, image_url = ?, download_url = ?, category = ?, badge = ?
               WHERE id = ?""",
            (title, title_en, description, description_en, price, image_url, download_url, category, badge, product_id)
        )
        conn.commit()


def delete_product(product_id):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def get_similar_products(product_id, category, limit=3):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE category = ? AND id != ? ORDER BY RANDOM() LIMIT ?",
            (category, product_id, limit)
        ).fetchall()


# ---------- Отзывы ----------
def add_review(product_id, username, rating, text):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO reviews (product_id, username, rating, text) VALUES (?, ?, ?, ?)",
            (product_id, username, rating, text)
        )
        conn.commit()


def get_reviews(product_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM reviews WHERE product_id = ? ORDER BY id DESC",
            (product_id,)
        ).fetchall()


def get_avg_rating(product_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as count FROM reviews WHERE product_id = ?",
            (product_id,)
        ).fetchone()
        if row and row["count"] > 0:
            return round(row["avg_r"], 1), row["count"]
        return None, 0


# ---------- Промокоды ----------
def get_promocode(code):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM promocodes WHERE code = ? AND active = 1 AND uses_left > 0",
            (code.upper(),)
        ).fetchone()


def use_promocode(code):
    with get_db() as conn:
        conn.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code.upper(),))
        conn.commit()


def get_all_promocodes():
    with get_db() as conn:
        return conn.execute("SELECT * FROM promocodes ORDER BY id DESC").fetchall()


def add_promocode(code, discount, uses_left=100):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO promocodes (code, discount, uses_left) VALUES (?, ?, ?)",
            (code.upper(), discount, uses_left)
        )
        conn.commit()


def delete_promocode(code):
    with get_db() as conn:
        conn.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        conn.commit()


# ---------- Заказы ----------
def create_order(product_id, payment_id, status="pending", buyer_email=None, promo_code=None, final_price=None, user_id=None):
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO orders
               (product_id, payment_id, status, buyer_email, promo_code, final_price, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (product_id, payment_id, status, buyer_email, promo_code, final_price, user_id)
        )
        conn.commit()


def mark_order_paid(payment_id):
    with get_db() as conn:
        conn.execute("UPDATE orders SET status = 'paid' WHERE payment_id = ?", (payment_id,))
        conn.commit()


def get_user_orders(user_id):
    with get_db() as conn:
        return conn.execute("""
            SELECT orders.*, products.title as product_title, products.download_url
            FROM orders
            LEFT JOIN products ON orders.product_id = products.id
            WHERE orders.user_id = ?
            ORDER BY orders.id DESC
        """, (user_id,)).fetchall()


def get_all_orders():
    with get_db() as conn:
        return conn.execute("""
            SELECT orders.*, products.title as product_title
            FROM orders
            LEFT JOIN products ON orders.product_id = products.id
            ORDER BY orders.id DESC LIMIT 100
        """).fetchall()


def get_orders_stats():
    with get_db() as conn:
        total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        paid_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(final_price), 0) FROM orders WHERE status = 'paid'").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        premium_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "revenue": round(revenue, 2),
            "users": users,
            "products": products,
            "premium_users": premium_users,
        }


# ---------- Пользователи ----------
def create_user(username, email, password_hash):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()


def get_user_by_username(username):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_email(email):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def update_user(user_id, **kwargs):
    if not kwargs:
        return
    fields = [f"{k} = ?" for k in kwargs.keys()]
    values = list(kwargs.values())
    values.append(user_id)
    with get_db() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()


# ---------- Избранное ----------
def toggle_favorite(user_id, product_id):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM favorites WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
            conn.commit()
            return False
        conn.execute("INSERT INTO favorites (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
        conn.commit()
        return True


def is_favorite(user_id, product_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT id FROM favorites WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        ).fetchone() is not None


def get_user_favorites(user_id):
    with get_db() as conn:
        return conn.execute("""
            SELECT products.* FROM favorites
            JOIN products ON favorites.product_id = products.id
            WHERE favorites.user_id = ?
            ORDER BY favorites.id DESC
        """, (user_id,)).fetchall()


# ---------- Корзина ----------
def add_to_cart(user_id, product_id):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        ).fetchone()
        if existing:
            conn.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = ?", (existing["id"],))
        else:
            conn.execute("INSERT INTO cart (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
        conn.commit()


def remove_from_cart(user_id, product_id):
    with get_db() as conn:
        conn.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        conn.commit()


def get_cart(user_id):
    with get_db() as conn:
        return conn.execute("""
            SELECT cart.id as cart_id, cart.quantity, products.*
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
            ORDER BY cart.id DESC
        """, (user_id,)).fetchall()


def get_cart_count(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row and row[0] else 0


def clear_cart(user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()


# ---------- FAQ ----------
def get_all_faq():
    with get_db() as conn:
        return conn.execute("SELECT * FROM faq ORDER BY sort_order, id").fetchall()


# ---------- Блог ----------
def get_all_posts():
    with get_db() as conn:
        return conn.execute("SELECT * FROM blog ORDER BY id DESC").fetchall()


def get_post_by_slug(slug):
    with get_db() as conn:
        return conn.execute("SELECT * FROM blog WHERE slug = ?", (slug,)).fetchone()


def add_post(title, slug, excerpt, content, image_url=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO blog (title, slug, excerpt, content, image_url) VALUES (?, ?, ?, ?, ?)",
            (title, slug, excerpt, content, image_url)
        )
        conn.commit()


def delete_post(post_id):
    with get_db() as conn:
        conn.execute("DELETE FROM blog WHERE id = ?", (post_id,))
        conn.commit()