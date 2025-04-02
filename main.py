import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from rss_parser import init_db, fetch_rss, get_news
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Підключаємо папку для статичних файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        # Отримуємо новини
        news = await get_news()  # Переконатися, що це асинхронна функція
        if not news:
            print("No news found.")
        # Повертаємо HTML-контент з новинами без використання шаблонів
        with open("index.html", "r") as file:
            content = file.read()
        
        # Заміщаємо місце для новин в HTML-шаблоні
        # Формат новин: [назва, URL, дата, джерело]
        news_list = ''.join([
            f'<div class="p-5 border border-blue-500 rounded-lg bg-gray-800 shadow-md w-3/4">'
            f'<a href="{item[1]}" target="_blank" class="text-xl font-semibold text-blue-300 hover:text-blue-500 transition">'
            f'{item[0]}</a>'
            f'<p class="text-sm text-gray-400">{item[2]}</p>'
            f'<p class="text-xs text-gray-500">Джерело: {item[3]}</p>'
            f'</div>' 
            for item in news
        ])
        
        content = content.replace("{{ news }}", news_list)  # Вставка новин в шаблон

        return HTMLResponse(content=content)
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return HTMLResponse(content=f"An error occurred: {str(e)}", status_code=500)

@app.on_event("startup")
async def startup_event():
    try:
        print("Initializing database...")
        await init_db()  # Переконатися, що ця функція асинхронна
        print("Fetching RSS data...")
        await fetch_rss()  # Переконатися, що ця функція асинхронна
    except Exception as e:
        print(f"Error during startup: {str(e)}")
