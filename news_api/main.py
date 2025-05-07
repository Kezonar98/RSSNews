# news_api/main.py
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db import get_news_item, get_latest_news, get_all_categories
from common.ai_rewriter import rewrite_or_get_cached

load_dotenv()

app = FastAPI(title="Cosmic News API", version="1.0.0")

origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "*").split(",")
    if o.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #Test! Later change to origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/news/{item_id}", tags=["News"])
async def news_item_endpoint(item_id: str):
    item = await get_news_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    rewritten_title, rewritten_body = await rewrite_or_get_cached(
        item_id, item["title"], item["link"]
    )

    item["rewritten_title"] = rewritten_title
    item["rewritten_body"] = rewritten_body
    return item


@app.get("/news", tags=["News"])
async def list_news(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: str | None = None
):
    return await get_latest_news(limit=limit, category=category, page=page)


@app.get("/categories", tags=["Categories"])
async def list_categories():
    return await get_all_categories()
