import feedparser
import aiosqlite

RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.cnn.com/rss/edition.rss",
]

DB_FILE = "news.db"

async def init_db():
    """Ініціалізація бази даних (створення таблиці новин)"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                link TEXT,
                published TEXT,
                source TEXT
            )"""
        )
        await db.commit()

async def fetch_rss():
    """Отримання новин із RSS-каналів та збереження у БД"""
    async with aiosqlite.connect(DB_FILE) as db:
        for url in RSS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Беремо перші 5 новин
                # Перевірка, чи новина вже є в базі, з урахуванням посилання (link)
                cursor = await db.execute(
                    "SELECT id FROM news WHERE link = ?",
                    (entry.link,)
                )
                existing_news = await cursor.fetchone()

                if existing_news:
                    # Якщо новина вже є, пропускаємо її
                    continue
                else:
                    # Якщо новина нова, перевіряємо кількість новин в базі
                    cursor = await db.execute("SELECT COUNT(*) FROM news")
                    count = await cursor.fetchone()

                    if count[0] >= 5:
                        # Якщо новин більше або дорівнює 5, видаляємо найстарішу
                        await db.execute(
                            "DELETE FROM news WHERE id = (SELECT MIN(id) FROM news)"
                        )

                    # Додаємо нову новину
                    await db.execute(
                        "INSERT INTO news (title, link, published, source) VALUES (?, ?, ?, ?)",
                        (entry.title, entry.link, entry.published, url),
                    )

        await db.commit()

async def get_news():
    """Отримує всі унікальні новини з бази та гарантує, що виводиться не більше 5 новин"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Вибираємо 5 новин, що є унікальними
        cursor = await db.execute("""
            SELECT DISTINCT title, link, published, source
            FROM news
            ORDER BY published DESC
            LIMIT 5
        """)
        return await cursor.fetchall()
