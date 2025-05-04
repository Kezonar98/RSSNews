# rss_fetcher/rss_parser.py
import os
from datetime import datetime, timezone
import feedparser
from dateutil import parser as date_parser
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from common.category_mapper import map_to_global_categories

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME         = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
RSS_FEEDS       = [
    url.strip()
    for url in os.getenv("RSS_FEEDS", "").split(",")
    if url.strip()
]
NEWS_LIMIT      = int(os.getenv("NEWS_LIMIT", "1000"))

client     = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

async def init_db():
    """Create a unique index on 'link' to avoid duplicates."""
    await collection.create_index("link", unique=True)

async def fetch_rss():
    """
    Fetch RSS entries, parse, extract categories via shared mapper,
    and upsert into MongoDB.
    """
    print("🔄 Starting RSS fetch...")
    for url in RSS_FEEDS:
        print(f"📡 Parsing feed: {url}")
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"⚠️ Feed parse error for {url}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            print(f"🔍 Entry: {title}")

            # Parse publication date
            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"⚠️ Error parsing date: {e}")
                pub_date = datetime.now(timezone.utc)

            # Map categories using shared mapper
            raw_terms = [tag.get("term", "") for tag in entry.get("tags", [])]
            categories = map_to_global_categories(raw_terms)

            news_item = {
                "title": title,
                "link": link,
                "published": pub_date,
                "source": url,
                "categories": categories,
                "created_at": datetime.now(timezone.utc),
            }

            # Upsert into MongoDB
            try:
                result = await collection.update_one(
                    {"link": link},
                    {"$set": news_item},
                    upsert=True
                )
                if result.matched_count:
                    print(f"🔄 Updated: {title}")
                elif result.upserted_id:
                    print(f"✅ Inserted: {title}")
            except Exception as e:
                print(f"❌ Upsert error for '{title}': {e}")

async def get_news():
    """
    Retrieve latest news documents sorted by published date descending.
    Primarily for local testing.
    """
    cursor = collection.find().sort("published", -1).limit(NEWS_LIMIT)
    return await cursor.to_list(length=NEWS_LIMIT)
