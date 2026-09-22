import sqlite3

DB_PATH = "devmarket.db"


def init_db():
    """Создаёт таблицы и заполняет товарами."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_url TEXT,
                download_url TEXT,
                category TEXT DEFAULT 'Прочее',
                badge TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                payment_id TEXT UNIQUE,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
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
            conn.commit()


def get_all_products():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()


def get_product(product_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def create_order(product_id, payment_id, status="pending"):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO orders (product_id, payment_id, status) VALUES (?, ?, ?)",
            (product_id, payment_id, status)
        )
        conn.commit()


def mark_order_paid(payment_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE orders SET status = 'paid' WHERE payment_id = ?",
            (payment_id,)
        )
        conn.commit()