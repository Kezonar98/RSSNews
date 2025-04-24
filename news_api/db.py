import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Environment variables from .env
MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME          = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "news")
DEFAULT_LIMIT    = int(os.getenv("DEFAULT_LIMIT", "5"))

# MongoDB connection
client     = AsyncIOMotorClient(MONGO_URI)
db         = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def get_all_categories():
    pipeline = [
        {"$unwind": "$categories"},
        {"$group": {"_id": "$categories"}},
        {"$sort": {"_id": 1}}
    ]
    result = await collection.aggregate(pipeline).to_list(length=100)
    return [r["_id"] for r in result]

async def get_latest_news(limit: int | None = None):
    """
    Returns the latest `limit` news, sorted by 'published' in descending order.
    If no limit is provided, it uses DEFAULT_LIMIT from .env.
    """
    if limit is None:
        limit = DEFAULT_LIMIT

    cursor = collection.find().sort("published", -1).limit(limit)
    news = await cursor.to_list(length=limit)

    # Convert ObjectId to string
    for item in news:
        if "_id" in item:
            item["id"] = str(item["_id"])
            del item["_id"]

    return news
