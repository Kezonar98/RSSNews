from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from db import get_latest_news, get_all_categories
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "5"))
cors_origins = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()] or ["*"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "API is up. Use /news and /categories."}

@app.get("/categories")
async def categories_endpoint():
    return await get_all_categories()

@app.get("/news")
async def news_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    category: str | None = Query(None)
):
    return await get_latest_news(limit=limit, category=category, page=page)
