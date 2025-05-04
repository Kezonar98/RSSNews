# rss_fetcher/main.py
import asyncio
from rss_parser import fetch_rss, init_db

async def periodic_fetch():
    """Initialize DB and then fetch periodically."""
    await init_db()
    while True:
        try:
            await fetch_rss()
        except Exception as e:
            print(f"❌ RSS fetch failed: {e}")
        await asyncio.sleep(60)  # Update every 60 seconds

if __name__ == "__main__":
    try:
        asyncio.run(periodic_fetch())
    except KeyboardInterrupt:
        print("Stopping RSS fetcher.")
