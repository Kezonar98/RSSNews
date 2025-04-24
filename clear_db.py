import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "rss_db"
COLLECTION_NAME = "news"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

async def clear_news():
    result = await collection.delete_many({})
    print(f"🧹 Deleted {result.deleted_count} documents from '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    asyncio.run(clear_news())
