import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME         = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
DEFAULT_LIMIT   = int(os.getenv("DEFAULT_LIMIT", "5"))

client     = AsyncIOMotorClient(MONGO_URI)
db         = client[DB_NAME]
collection = db[COLLECTION_NAME]

BASE_CATEGORIES = [
    "World", "Politics", "Technology", "Science", "Space",
    "Health", "Games", "Anime", "Sport", "Economy", "Culture"
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "World":       ["world", "country", "africa", "asia", "europe", "america", "canada", "australia"],
    "Politics":    ["politic", "government", "election", "president", "parliament", "senate", "minister"],
    "Technology":  ["technology", "tech", "computer", "software", "hardware", "ai", "artificial"],
    "Science":     ["science", "research", "study", "physics", "biology", "chemistry", "astronomy", "scientist"],
    "Environment": ["environment", "climate", "nature", "pollution", "wildlife", "conservation"],
    "Crime":       ["crime", "criminal", "mafia", "bandit", "gang", "murder", "assault", "terror"],
    "Business":    ["business", "company", "corporation", "startup", "entrepreneur", "investment"],
    "Space":       ["space", "nasa", "astronaut", "galaxy", "planet", "rocket"],
    "Health":      ["health", "medical", "disease", "medicine", "hospital"],
    "Games":       ["game", "gaming", "videogame", "esport"],
    "Anime":       ["anime", "manga", "otaku", "cartoon"],
    "Sport":       ["sport", "football", "soccer", "basketball", "tennis", "cricket", "olympic", "chess"],
    "Economy":     ["economy", "finance", "market", "stock", "bank"],
    "Culture":     ["culture", "art", "music", "film", "book", "literature", "theater"],
}


def _map_to_base(raw: str) -> str | None:
    low = raw.lower()
    for base, keys in CATEGORY_KEYWORDS.items():
        for kw in keys:
            if kw in low:
                return base
    return None


async def get_all_categories() -> list[str]:
    raw_cats = await collection.distinct("categories")
    used = { _map_to_base(c) for c in raw_cats if _map_to_base(c) }
    return [c for c in BASE_CATEGORIES if c in used]


async def get_latest_news(
    limit: int | None = None,
    category: str | None = None,
    page: int = 1
) -> dict[str, object]:
    if limit is None:
        limit = DEFAULT_LIMIT
    skip_count = (page - 1) * limit

    filter_q: dict = {}
    if category:
        kws = CATEGORY_KEYWORDS.get(category, [])
        pattern = "|".join(re.escape(kw) for kw in kws)
        filter_q["categories"] = {"$elemMatch": {"$regex": pattern, "$options": "i"}}

    total_count = await collection.count_documents(filter_q)
    total_pages = (total_count + limit - 1) // limit

    cursor = (
        collection.find(filter_q)
        .sort("published", -1)
        .skip(skip_count)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    items = []
    for d in docs:
        d["id"] = str(d["_id"])
        del d["_id"]
        items.append(d)

    return {"items": items, "totalPages": total_pages}
