import sqlite3

DB_PATH = "devmarket.db"


def init_db():
    """Создаёт таблицы и заполняет тестовыми товарами."""
    with sqlite3.connect(DB_PATH) as conn:
        # Таблица товаров
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

        # Таблица заказов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                payment_id TEXT UNIQUE,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Заполняем товарами только если таблица пустая
        cur = conn.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] == 0:
            products = [
                (
                    "Шаблон Telegram-бота PlayWatch",
                    "Готовый Telegram-бот на Python: погода, курсы крипты, игры, цитаты и шутки. Чистая модульная архитектура, токен в .env, запуск за 5 минут.",
                    499.00,
                    "https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?w=900",
                    "https://example.com/bot.zip",
                    "Боты",
                    "ХИТ"
                ),
                (
                    "Шаблон сайта-каталога игр PlayWatch",
                    "Flask-сайт для каталога игр с админкой, поиском, фильтрами, отзывами и избранным. Готовая база, загрузка обложек, Bootstrap 5.",
                    799.00,
                    "https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?w=900",
                    "https://example.com/site-catalog.zip",
                    "Сайты",
                    "NEW"
                ),
                (
                    "Шаблон сайта-магазина DevMarket",
                    "Готовый интернет-магазин на Flask с приёмом оплаты через ЮKassa, базой товаров, красивым Aurora-дизайном.",
                    999.00,
                    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=900",
                    "https://example.com/shop-site.zip",
                    "Сайты",
                    "TOP"
                ),
                (
                    "Шаблон Telegram-магазина",
                    "Бот-магазин с корзиной, оформлением заказа и оплатой через ЮKassa. Админка для управления товарами.",
                    1299.00,
                    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=900",
                    "https://example.com/shop-bot.zip",
                    "Боты",
                    "PRO"
                ),
                (
                    "Гайд: деплой бота и сайта на Render",
                    "PDF-инструкция на 25 страниц: как залить проект на GitHub, поднять бота и сайт на Render, настроить переменные окружения и UptimeRobot.",
                    199.00,
                    "https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?w=900",
                    "https://example.com/guide-render.pdf",
                    "Гайды",
                    None
                ),
                (
                    "100 промптов для ChatGPT 2026",
                    "Сборник из 100+ проверенных промптов для маркетинга, кода, текстов, дизайна и бизнеса. Работают с GPT-4, Claude и DeepSeek.",
                    349.00,
                    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=900",
                    "https://example.com/prompts.pdf",
                    "Гайды",
                    "TOP"
                ),
                (
                    "Парсер маркетплейсов WB, Ozon, Яндекс.Маркет",
                    "Python-скрипт для сбора цен и отзывов с Wildberries, Ozon и Яндекс.Маркета. Экспорт в Excel, уведомления в Telegram.",
                    1499.00,
                    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=900",
                    "https://example.com/parser.zip",
                    "Скрипты",
                    "PRO"
                ),
                (
                    "Telegram-бот для приёма заявок",
                    "Готовый бот для приёма заявок с сайта или соцсетей. Сохраняет в Google Sheets и отправляет уведомления админу.",
                    899.00,
                    "https://images.unsplash.com/photo-1611606063065-ee7946f0787a?w=900",
                    "https://example.com/leads-bot.zip",
                    "Боты",
                    "NEW"
                ),
            ]

            for p in products:
                conn.execute(
                    "INSERT INTO products (title, description, price, image_url, download_url, category, badge) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    p
                )
            conn.commit()


def get_all_products():
    """Возвращает все товары, новые — первыми."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()


def get_product(product_id):
    """Возвращает товар по ID."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def create_order(product_id, payment_id, status="pending"):
    """Создаёт запись о заказе."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO orders (product_id, payment_id, status) VALUES (?, ?, ?)",
            (product_id, payment_id, status)
        )
        conn.commit()


def mark_order_paid(payment_id):
    """Помечает заказ как оплаченный."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE orders SET status = 'paid' WHERE payment_id = ?",
            (payment_id,)
        )
        conn.commit()