# news_api/db.py
import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson import ObjectId
from common.category_mapper import map_to_global_categories, GLOBAL_CATEGORY_MAPPING
from typing import Any, Dict
from urllib.parse import urlparse
from datetime import datetime

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME         = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
DEFAULT_LIMIT   = int(os.getenv("DEFAULT_LIMIT", "5"))

client     = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]


async def get_all_categories() -> list[str]:
    """Return list of global categories actually used in the collection."""
    # distinct returns distinct values stored in the `categories` field (strings).
    raw_cats = await collection.distinct("categories")
    # Map each raw category to global ones, dedupe, keep order.
    # `map_to_global_categories` expects list[str] and returns list of global categories.
    mapped = map_to_global_categories(raw_cats)
    return mapped


def _extract_source_from_link(link: str) -> str:
    """Return a short host/source string extracted from a URL."""
    try:
        p = urlparse(link or "")
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _to_iso(dt: Any) -> str:
    """Normalize datetime-like values to ISO8601 string for the frontend."""
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        # use isoformat without microseconds for brevity
        return dt.isoformat()
    try:
        # fallback: try to call isoformat
        return dt.isoformat()
    except Exception:
        return ""


async def get_latest_news(limit: int | None = None, category: str | None = None, page: int = 1) -> dict:
    """
    Fetch paginated news items, optionally filtered by a global category.
    Returns dict with 'items' and 'totalPages'.

    Note: This function returns raw DB documents but also normalizes the shape
    expected by the frontend (title, description, source, published ISO string).
    """
    limit = limit or DEFAULT_LIMIT
    skip  = (page - 1) * limit

    filter_q = {}
    if category:
        # If provided a global category name, build pattern from keywords
        keywords = GLOBAL_CATEGORY_MAPPING.get(category, [])
        pattern  = "|".join(re.escape(kw) for kw in keywords)
        if pattern:
            filter_q["categories"] = {"$elemMatch": {"$regex": pattern, "$options": "i"}}

    total = await collection.count_documents(filter_q)
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    cursor = collection.find(filter_q).sort("published", -1).skip(skip).limit(limit)
    docs   = await cursor.to_list(length=limit)

    items = []
    for d in docs:
        # normalize common fields for frontend compatibility
        title = d.get("rewritten_title") or d.get("original_title") or ""
        description = (d.get("rewritten_body") or "")[:300]  # short excerpt
        source = _extract_source_from_link(d.get("original_link") or d.get("link", ""))
        published = _to_iso(d.get("published"))
        item = dict(d)  # shallow copy
        # ensure id field is string
        item["id"] = str(item.get("_id") or item.get("id", ""))
        item.pop("_id", None)
        # normalized fields expected by frontend
        item["title"] = title
        item["description"] = description
        item["source"] = source
        item["published"] = published
        # ensure boolean present
        item["is_rewritten"] = bool(item.get("is_rewritten", False))
        # include slug if present
        if item.get("slug"):
            item["slug"] = item["slug"]
        else:
            item["slug"] = ""
        items.append(item)

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

    # Normalize fields for frontend compatibility
    doc["title"] = doc.get("rewritten_title") or doc.get("original_title") or ""
    doc["description"] = (doc.get("rewritten_body") or "")[:300]
    doc["source"] = _extract_source_from_link(doc.get("original_link") or doc.get("link", ""))
    # published to ISO
    doc["published"] = _to_iso(doc.get("published"))
    doc["is_rewritten"] = bool(doc.get("is_rewritten", False))
    # include slug
    doc["slug"] = doc.get("slug", "")

    return doc


async def get_news_by_slug(slug: str) -> dict | None:
    """Fetch a single news document by its slug."""
    try:
        doc = await collection.find_one({"slug": slug})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)

    doc["title"] = doc.get("rewritten_title") or doc.get("original_title") or ""
    doc["description"] = (doc.get("rewritten_body") or "")[:300]
    doc["source"] = _extract_source_from_link(doc.get("original_link") or doc.get("link", ""))
    doc["published"] = _to_iso(doc.get("published"))
    doc["is_rewritten"] = bool(doc.get("is_rewritten", False))
    doc["slug"] = doc.get("slug", "")

    return doc
