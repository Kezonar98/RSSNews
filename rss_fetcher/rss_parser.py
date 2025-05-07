import os
import asyncio
from datetime import datetime, timezone

import feedparser
from dateutil import parser as date_parser
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from common.category_mapper import map_to_global_categories
from common.ai_rewriter import rewrite_or_get_cached

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
    await collection.create_index("link", unique=True)


async def fetch_rss():
    print("🔄 Starting RSS fetch...")
    for url in RSS_FEEDS:
        print(f"📡 Parsing feed: {url}")
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"⚠️ Feed parse error for {url}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()
            print(f"🔍 Entry: {title}")

            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)

            raw_terms  = [tag.get("term", "") for tag in entry.get("tags", [])]
            categories = map_to_global_categories(raw_terms)

            try:
                rewritten_title, rewritten_body = await rewrite_or_get_cached(link, title, link)
            except Exception as e:
                print(f"❌ [REWRITER] Failed to rewrite '{title}': {e}")
                rewritten_title, rewritten_body = title, ""

            news_item = {
                "title": title,
                "link": link,
                "published": pub_date,
                "source": url,
                "categories": categories,
                "created_at": datetime.now(timezone.utc),
                "rewritten_title": rewritten_title,
                "rewritten_body": rewritten_body,
            }

            try:
                res = await collection.update_one(
                    {"link": link},
                    {"$set": news_item},
                    upsert=True
                )
                action = "Updated" if res.matched_count else "Inserted"
                print(f"🔄 {action}: {title}")
            except Exception as e:
                print(f"❌ Upsert error for '{title}': {e}")
