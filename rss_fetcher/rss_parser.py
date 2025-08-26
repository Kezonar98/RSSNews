# rss_fetcher/rss_parser.py
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

import feedparser
from dateutil import parser as date_parser
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
import socket

from common.category_mapper import map_to_global_categories
from common.ai_rewriter import rewrite_or_get_cached

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
RSS_FEEDS = [
    url.strip()
    for url in os.getenv("RSS_FEEDS", "").split(",")
    if url.strip()
]
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "1000"))

# If you want to force remote moderation API, set MODERATION_SERVICE_URL env var.
# Example: http://moderation_service:8002/moderate/title
MODERATION_SERVICE_URL = os.getenv("MODERATION_SERVICE_URL", "http://moderation_service:8002/moderate/title")

client = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]


async def _call_remote_moderation(session: aiohttp.ClientSession, text: str, timeout: int = 5) -> Optional[str]:
    """
    Call the remote moderation service endpoint to clean a title.
    Returns cleaned title on success, None on failure.
    """
    try:
        async with session.post(MODERATION_SERVICE_URL, json={"text": text}, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                # remote API may return cleaned text in different shapes.
                # try common keys: cleaned_text, cleaned_title, title
                for key in ("cleaned_text", "cleaned_title", "title", "cleaned"):
                    if key in data:
                        val = data[key]
                        if isinstance(val, str) and val.strip():
                            return val.strip()
                # fallback: maybe wrapped in moderation.title_cleanup.cleaned_title
                if isinstance(data, dict):
                    # try nested lookups
                    tc = data.get("title_cleanup") or data.get("moderation", {}).get("title_cleanup")
                    if isinstance(tc, dict):
                        ct = tc.get("cleaned_title") or tc.get("cleaned")
                        if isinstance(ct, str) and ct.strip():
                            return ct.strip()
            else:
                # non-200 response
                print(f"[moderation-client] Remote moderation returned status {resp.status}")
    except asyncio.TimeoutError:
        print("[moderation-client] Remote moderation timed out")
    except aiohttp.ClientConnectorError as e:
        print(f"[moderation-client] Connector error: {e}")
    except Exception as e:
        print(f"[moderation-client] Unexpected error when calling remote moderation: {e}")
    return None


def _local_title_cleanup_fallback(text: str) -> str:
    """
    Very small local fallback cleanup if agent import is not available.
    This is a best-effort strip that removes common LLM artifacts.
    """
    cleaned = text or ""
    # Remove common LLM prefixes
    cleaned = cleaned.strip()
    cleaned = __import__("re").sub(r'(?i)\b(rewritten\s*title:?|rewrite:?|title:)\b', '', cleaned)
    # Remove bracketed inserts and "Note:" / "Update:" lines
    cleaned = __import__("re").sub(r'\[.*?\]', ' ', cleaned)
    cleaned = __import__("re").sub(r'(?im)^\s*(note:|update:).*$', ' ', cleaned)
    # Remove quotes and excessive punctuation
    cleaned = cleaned.replace('"', '').replace("'", "")
    cleaned = __import__("re").sub(r'[\*\#\>\<\=]{2,}', ' ', cleaned)
    # Split on common separators and pick best candidate
    parts = __import__("re").split(r';|\||\n| in ', cleaned)
    candidates = [p.strip() for p in parts if p.strip() and len(p.split()) >= 3]
    if candidates:
        # choose candidate closest to 8-12 words (headline sweet spot)
        candidates_sorted = sorted(candidates, key=lambda x: abs(len(x.split()) - 10))
        best = candidates_sorted[0]
    else:
        best = cleaned.strip()
    # final trim
    best = best.strip(' .,-–—')
    if not best or len(best) < 5:
        return "Untitled"
    return best


async def clean_title(text: str) -> str:
    """
    Try to clean title via remote moderation API first.
    If remote fails, try to import local TitleModerationAgent and use it.
    If import fails, fall back to a simple heuristic cleanup.
    """
    text = (text or "").strip()
    if not text:
        return ""

    # Attempt remote moderation API first.
    # Use a short timeout and single-shot client session.
    try:
        # Quick DNS check to avoid long socket hangups if host unknown
        parsed = MODERATION_SERVICE_URL.split("://")[-1].split("/")[0]
        host = parsed.split(":")[0]
        try:
            # Try to resolve host name; if it fails, skip remote call
            socket.getaddrinfo(host, None)
            can_resolve = True
        except socket.gaierror:
            can_resolve = False

        if can_resolve:
            async with aiohttp.ClientSession() as session:
                cleaned = await _call_remote_moderation(session, text)
                if cleaned:
                    return cleaned
        else:
            print("[moderation-client] Remote moderation hostname not resolvable, skipping remote call.")
    except Exception as e:
        # defensive: any unexpected error with remote call flows to local fallback
        print(f"[moderation-client] Error during remote moderation attempt: {e}")

    # Remote failed or not available → try local import of TitleModerationAgent
    try:
        # dynamic import to avoid import errors when running in separate container
        mod = __import__("moderation_service.agents", fromlist=["TitleModerationAgent"])
        TitleModerationAgent = getattr(mod, "TitleModerationAgent", None)
        if TitleModerationAgent:
            agent = TitleModerationAgent()
            # If agent is synchronous, run it in executor to avoid blocking event loop
            if asyncio.iscoroutinefunction(agent.run):
                cleaned = await agent.run(text)
            else:
                loop = asyncio.get_event_loop()
                cleaned = await loop.run_in_executor(None, lambda: agent.run(text))
            if isinstance(cleaned, dict):
                # If agent returns dict, try to extract cleaned_title key
                for key in ("cleaned_title", "cleaned_text", "title"):
                    if key in cleaned and isinstance(cleaned[key], str) and cleaned[key].strip():
                        return cleaned[key].strip()
                # fallback to original string representation
                return str(cleaned)
            elif isinstance(cleaned, str) and cleaned.strip():
                return cleaned.strip()
    except ModuleNotFoundError:
        print("[moderation-client] Local TitleModerationAgent not found, using heuristic fallback.")
    except Exception as e:
        print(f"[moderation-client] Error running local TitleModerationAgent: {e}")

    # Final fallback: simple heuristic cleanup
    return _local_title_cleanup_fallback(text)


async def init_db():
    await collection.create_index("link", unique=True)


async def fetch_rss():
    """
    Fetch RSS feeds, rewrite articles with Llama, 
    clean titles via moderation service (remote or local) before saving.
    """
    print("🔄 Starting RSS fetch...")
    for url in RSS_FEEDS:
        print(f"📡 Parsing feed: {url}")
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"⚠️ Feed parse error for {url}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            raw_title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            print(f"🔍 Entry: {raw_title}")

            # Parse publication date
            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)

            # Map categories
            raw_terms = [tag.get("term", "") for tag in entry.get("tags", [])]
            categories = map_to_global_categories(raw_terms)

            # Default rewritten fields
            rewritten_title = None
            rewritten_body = None
            is_rewritten = False

            # Attempt rewrite with Llama
            try:
                new_title, new_body = await rewrite_or_get_cached(link, raw_title, link)

                # If the rewritten body is valid, clean the rewritten title through moderation
                if new_body and not new_body.startswith(("[ERROR]", "[WARNING]")):
                    # Clean rewritten title using remote API or local agent fallback
                    try:
                        cleaned_title = await clean_title(new_title if new_title else raw_title)
                    except Exception as e:
                        print(f"❌ Error during title cleaning fallback: {e}")
                        cleaned_title = new_title if new_title else raw_title

                    rewritten_title = cleaned_title.strip() if cleaned_title else None
                    rewritten_body = new_body.strip() if new_body else None
                    is_rewritten = True
                    print(f"✅ Rewritten & cleaned: {raw_title}")
                else:
                    print(f"⚠️ Rewrite returned empty/error for '{raw_title}'")
            except Exception as e:
                print(f"❌ [REWRITER] Failed to rewrite '{raw_title}': {e}")

            # Prepare final news item
            news_item = {
                "title": raw_title,
                "link": link,
                "published": pub_date,
                "source": url,
                "categories": categories,
                "created_at": datetime.now(timezone.utc),
                "rewritten_title": rewritten_title,
                "rewritten_body": rewritten_body,
                "is_rewritten": is_rewritten,
            }

            # Save to DB
            try:
                res = await collection.update_one(
                    {"link": link},
                    {"$set": news_item},
                    upsert=True
                )
                action = "Updated" if res.matched_count else "Inserted"
                print(f"🔄 {action}: {raw_title} (is_rewritten={is_rewritten})")
            except Exception as e:
                print(f"❌ Upsert error for '{raw_title}': {e}")
