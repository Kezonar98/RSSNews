import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import feedparser
from dateutil import parser as date_parser
from dotenv import load_dotenv

CATEGORY_MAP = {
    "world": "World",
    "politics": "Politics",
    "tech": "Technology",
    "science": "Science",
    "health": "Health",
    "games": "Games",
    "anime": "Anime",
    "sport": "Sport",
    "economy": "Economy",
    "culture": "Culture",
}

def normalize_category(cat: str) -> str:
    if not cat:
        return None
    normalized = CATEGORY_MAP.get(cat.lower().strip())
    return normalized or cat.strip()

load_dotenv()

# Load configuration from environment
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")

# RSS feed URLs (comma-separated in .env)
RSS_FEEDS = [url.strip() for url in os.getenv("RSS_FEEDS", "").split(",") if url.strip()]

# Maximum news items to retrieve
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "1000"))

# Initialize MongoDB client and collection
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def init_db():
    """
    Create a unique index on 'link' field to avoid duplicates.
    """
    await collection.create_index("link", unique=True)

async def fetch_rss():
    """
    Fetch RSS entries, parse, extract categories, and upsert into MongoDB.
    """
    print("🔄 Starting RSS fetch...")
    for url in RSS_FEEDS:
        print(f"📡 Parsing feed: {url}")
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"⚠️ Feed parse error for {url}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            print(f"🔍 Found entry: {entry.title} | {entry.get('published', 'N/A')}")

            # Parse publication date
            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"⚠️ Error parsing date: {e}")
                pub_date = datetime.now(timezone.utc)

            # Extract categories/tags if available
            raw_tags = entry.get("tags", [])
            categories = list({
               normalize_category(tag.get('term')) 
               for tag in raw_tags if tag.get('term')
})

            news_item = {
                "title": entry.title,
                "link": entry.link,
                "published": pub_date,
                "source": url,
                "categories": categories,
                "created_at": datetime.now(timezone.utc)
            }

            # Upsert into MongoDB
            try:
                result = await collection.update_one(
                    {"link": entry.link},
                    {"$set": news_item},
                    upsert=True
                )
                if result.matched_count:
                    print(f"🔄 Updated: {entry.title}")
                elif result.upserted_id:
                    print(f"✅ Inserted new: {entry.title}")
            except Exception as e:
                print(f"❌ Error upserting: {entry.title} — {e}")

async def get_news():
    """
    Retrieve latest news documents sorted by published date descending.
    """
    cursor = collection.find().sort("published", -1).limit(NEWS_LIMIT)
    return await cursor.to_list(length=NEWS_LIMIT)
