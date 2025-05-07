# news_api/db.py

import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson import ObjectId
from common.category_mapper import map_to_global_categories, GLOBAL_CATEGORY_MAPPING

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME         = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
DEFAULT_LIMIT   = int(os.getenv("DEFAULT_LIMIT", "5"))

client     = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]


async def get_all_categories() -> list[str]:
    """Return list of global categories actually used in the collection."""
    raw_cats = await collection.distinct("categories")
    # Map each raw category to global ones, dedupe, keep order
    mapped = map_to_global_categories(raw_cats)
    return mapped


async def get_latest_news(limit: int | None = None, category: str | None = None, page: int = 1) -> dict:
    """
    Fetch paginated news items, optionally filtered by a global category.
    Returns dict with 'items' and 'totalPages'.
    """
    limit = limit or DEFAULT_LIMIT
    skip  = (page - 1) * limit

    filter_q = {}
    if category:
        keywords = GLOBAL_CATEGORY_MAPPING.get(category, [])
        pattern  = "|".join(re.escape(kw) for kw in keywords)
        filter_q["categories"] = {"$elemMatch": {"$regex": pattern, "$options": "i"}}

    total = await collection.count_documents(filter_q)
    total_pages = (total + limit - 1) // limit

    cursor = collection.find(filter_q).sort("published", -1).skip(skip).limit(limit)
    docs   = await cursor.to_list(length=limit)

    items = []
    for d in docs:
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        items.append(d)

    return {"items": items, "totalPages": total_pages}


async def get_news_item(item_id: str) -> dict | None:
    """Fetch a single news document by its ObjectId string."""
    try:
        doc = await collection.find_one({"_id": ObjectId(item_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc
