# news_api/main.py
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db import get_latest_news, get_all_categories
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Cosmic News API",
    description="Provides the latest news with optional category filtering",
    version="1.0.0",
)

# CORS setup
origins = [
    o.strip() 
    for o in os.getenv("CORS_ORIGINS", "*").split(",") 
    if o.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "5"))


@app.get("/", tags=["Root"])
async def root():
    return {"message": "API is up. Use /news and /categories."}


@app.get("/categories", tags=["Categories"])
async def categories_endpoint():
    try:
        return await get_all_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {e}")


@app.get("/news", tags=["News"])
async def news_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    category: str | None = Query(None),
):
    try:
        return await get_latest_news(limit=limit, category=category, page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {e}")
