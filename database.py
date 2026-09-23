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
                description TEXT,
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
        """)

        cur = conn.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            products = [
                (
                    "Шаблон Telegram-бота PlayWatch",
                    "Готовый Telegram-бот на Python: погода, курсы крипты, игры, цитаты и шутки. Чистая модульная архитектура, токен в .env, запуск за 5 минут.",
                    499.00,
                    "https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?w=900",
                    "https://drive.google.com/uc?export=download&id=1HLlCFcHwPvs3dEgMD1H6BN4bmiPtM_gS",
                    "Боты",
                    "ХИТ"
                ),
                (
                    "100 промптов для ChatGPT 2026",
                    "Сборник из 100+ проверенных промптов для маркетинга, кода, текстов, дизайна и бизнеса. Работают с GPT-4, Claude и DeepSeek. Формат PDF.",
                    349.00,
                    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=900",
                    "https://drive.google.com/uc?export=download&id=1Pcbb7S8HaHPN-MR66mIEZ8QIrp_ikQhA",
                    "Гайды",
                    "TOP"
                ),
                (
                    "Гайд: деплой бота и сайта на Render",
                    "PDF-инструкция на 25 страниц: как залить проект на GitHub, поднять бота и сайт на Render, настроить переменные окружения и UptimeRobot.",
                    199.00,
                    "https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?w=900",
                    "https://drive.google.com/uc?export=download&id=1ATcUqgFxsA39-sSe1Y3_pcYC4dBFTSfI",
                    "Гайды",
                    None
                ),
            ]
            for p in products:
                conn.execute(
                    "INSERT INTO products (title, description, price, image_url, download_url, category, badge) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    p
                )

            # Стартовые промокоды
            conn.execute("INSERT INTO promocodes (code, discount, uses_left) VALUES (?, ?, ?)", ("WELCOME10", 10, 999))
            conn.execute("INSERT INTO promocodes (code, discount, uses_left) VALUES (?, ?, ?)", ("DEVMARKET20", 20, 100))

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
            "SELECT * FROM products WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC",
            (f"%{query}%", f"%{query}%")
        ).fetchall()


def add_product(title, description, price, image_url, download_url, category, badge):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO products
               (title, description, price, image_url, download_url, category, badge)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, description, price, image_url, download_url, category, badge)
        )
        conn.commit()


def delete_product(product_id):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def get_similar_products(product_id, category, limit=3):
    """Возвращает похожие товары из той же категории."""
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
        conn.execute(
            "UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?",
            (code.upper(),)
        )
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
def create_order(product_id, payment_id, status="pending", buyer_email=None, promo_code=None, final_price=None):
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO orders
               (product_id, payment_id, status, buyer_email, promo_code, final_price)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product_id, payment_id, status, buyer_email, promo_code, final_price)
        )
        conn.commit()


def mark_order_paid(payment_id):
    with get_db() as conn:
        conn.execute("UPDATE orders SET status = 'paid' WHERE payment_id = ?", (payment_id,))
        conn.commit()


def get_all_orders():
    with get_db() as conn:
        return conn.execute("""
            SELECT orders.*, products.title as product_title
            FROM orders
            LEFT JOIN products ON orders.product_id = products.id
            ORDER BY orders.id DESC
            LIMIT 50
        """).fetchall()


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