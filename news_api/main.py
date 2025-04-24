from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import get_latest_news, get_all_categories
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "5"))

cors_origins = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

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
    return {"message": "API працює! Використовуйте /news для отримання новин."}

@app.get("/news")
async def news_endpoint(limit: int = DEFAULT_LIMIT):
    return await get_latest_news(limit)

@app.get("/categories")
async def categories_endpoint():
    return await get_all_categories()
