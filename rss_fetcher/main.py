import asyncio
from rss_parser import fetch_rss, init_db

async def periodic_fetch():
    while True:
        await fetch_rss()
        print("🕒 Оновлено RSS")
        await asyncio.sleep(60)  #Update every 60 seconds

async def main():
    await init_db()
    await periodic_fetch()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Завершення роботи.")
