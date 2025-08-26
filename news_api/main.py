# news_api/main.py
import os
import math
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from db import get_news_item, get_latest_news, get_all_categories

load_dotenv()

logger = logging.getLogger("news_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Cosmic News API", version="1.0.0")

origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "*").split(",")
    if o.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Test! Later change to origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/news/{item_id}", tags=["News"])
async def news_item_endpoint(item_id: str):
    """
    Return a single news item only if it has been rewritten by AI (is_rewritten=True).
    This prevents triggering on-demand rewriting when a user opens the article.
    """
    item = await get_news_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.get("is_rewritten"):
        # Rewritten version not available yet — do not perform rewriting here.
        raise HTTPException(status_code=404, detail="Rewritten version not available")

    # Return stored rewritten fields (preserve original fields as well)
    return item


@app.get("/news", tags=["News"])
async def list_news(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: str | None = None
):
    """
    Return paginated list of news that are already rewritten.
    We call get_latest_news() (existing DB helper), then filter items that have is_rewritten=True.
    Pagination is recalculated from the filtered set to guarantee consistent client pages.
    """
    raw = await get_latest_news(limit=limit, category=category, page=1)  # request page 1 to get the full chunk
    # raw can be either a dict {items, totalPages,...} or a list. Handle both cases defensively.
    items = []
    if isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
    elif isinstance(raw, list):
        items = raw
    else:
        # Unexpected shape — just return empty
        items = []

    # Filter only rewritten items
    rewritten_items = [i for i in items if i.get("is_rewritten")]

    # Recompute pagination based on filtered items
    total_items = len(rewritten_items)
    total_pages = max(1, math.ceil(total_items / limit))

    # Slice for requested page
    start = (page - 1) * limit
    end = start + limit
    page_items = rewritten_items[start:end]

    return {
        "items": page_items,
        "totalPages": total_pages,
        "page": page,
        "limit": limit,
        "totalItems": total_items,
    }


@app.get("/categories", tags=["Categories"])
async def list_categories():
    return await get_all_categories()
