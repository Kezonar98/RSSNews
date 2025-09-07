# rss_fetcher/rss_parser.py
import os
import asyncio
import socket
import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
from dateutil import parser as date_parser
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp
import logging
import re
import json
import unicodedata

from common.category_mapper import map_to_global_categories
from common.ai_rewriter import rewrite_or_get_cached

load_dotenv()

logger = logging.getLogger("rss_fetcher")
logger.setLevel(logging.INFO)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
DB_NAME = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
RSS_FEEDS = [
    url.strip()
    for url in os.getenv("RSS_FEEDS", "").split(",")
    if url.strip()
]
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "1000"))

MODERATION_ARTICLE_URL = os.getenv("MODERATION_ARTICLE_URL", "").strip()
MODERATION_TITLE_URL = os.getenv("MODERATION_TITLE_URL", "").strip()
MODERATION_SERVICE_BASE = os.getenv("MODERATION_SERVICE_BASE", "").strip()
LEGACY_MOD_URL = os.getenv("MODERATION_SERVICE_URL", "").strip()

# How long (seconds) to wait for moderation service at startup; default 30s
MODERATION_WAIT_TIMEOUT = int(os.getenv("MODERATION_WAIT_TIMEOUT", "30"))

PREVIEW_LEN = 1000

def _normalize_endpoints():
    global MODERATION_ARTICLE_URL, MODERATION_TITLE_URL, MODERATION_SERVICE_BASE, LEGACY_MOD_URL
    if MODERATION_ARTICLE_URL and MODERATION_TITLE_URL:
        return
    if MODERATION_SERVICE_BASE:
        base = MODERATION_SERVICE_BASE.rstrip("/")
        MODERATION_ARTICLE_URL = MODERATION_ARTICLE_URL or f"{base}/moderate/article"
        MODERATION_TITLE_URL = MODERATION_TITLE_URL or f"{base}/moderate/title"
        return
    if LEGACY_MOD_URL:
        u = LEGACY_MOD_URL.rstrip("/")
        if u.endswith("/moderate/article"):
            MODERATION_ARTICLE_URL = MODERATION_ARTICLE_URL or u
            MODERATION_TITLE_URL = MODERATION_TITLE_URL or u.replace("/moderate/article", "/moderate/title")
        elif u.endswith("/moderate/title"):
            MODERATION_TITLE_URL = MODERATION_TITLE_URL or u
            MODERATION_ARTICLE_URL = MODERATION_ARTICLE_URL or u.replace("/moderate/title", "/moderate/article")
        else:
            base = u
            MODERATION_ARTICLE_URL = MODERATION_ARTICLE_URL or f"{base}/moderate/article"
            MODERATION_TITLE_URL = MODERATION_TITLE_URL or f"{base}/moderate/title"
        return
    MODERATION_ARTICLE_URL = MODERATION_ARTICLE_URL or "http://moderation_service:8002/moderate/article"
    MODERATION_TITLE_URL = MODERATION_TITLE_URL or "http://moderation_service:8002/moderate/title"

_normalize_endpoints()

client = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

# -------------------- Helpers for waiting services --------------------

async def wait_for_mongo(timeout: float = 60.0, interval: float = 1.0):
    """
    Wait for MongoDB to accept connections. Uses motor client admin ping.
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + timeout
    probe_client = AsyncIOMotorClient(MONGO_URI)
    while time.time() < deadline:
        try:
            # motor supports await probe_client.admin.command('ping')
            await probe_client.admin.command('ping')
            logger.info("[wait_for_mongo] MongoDB is available")
            return True
        except Exception as e:
            logger.info(f"[wait_for_mongo] waiting for MongoDB at {MONGO_URI}: {e}")
            await asyncio.sleep(interval)
    raise RuntimeError(f"[wait_for_mongo] MongoDB not available after {timeout}s (uri={MONGO_URI})")

async def wait_for_http_service(url: str, timeout: float = 30.0, interval: float = 1.0):
    """
    Optional: wait until a simple HTTP GET to url returns 200.
    Returns True if available, False on timeout (non-fatal).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as resp:
                    if resp.status == 200:
                        logger.info(f"[wait_for_http_service] {url} is up")
                        return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    logger.warning(f"[wait_for_http_service] Timeout waiting for {url}")
    return False

# -------------------- Moderation Helpers --------------------
async def _post_json(session: aiohttp.ClientSession, url: str, payload: dict, timeout: int = 6):
    try:
        async with session.post(url, json=payload, timeout=timeout) as resp:
            status = resp.status
            text = await resp.text()
            try:
                data = await resp.json()
                return status, data
            except Exception:
                return status, text
    except asyncio.TimeoutError:
        logger.warning(f"[moderation-client] Timeout when calling {url}")
        return None, None
    except aiohttp.ClientConnectorError as e:
        logger.warning(f"[moderation-client] Connector error to {url}: {e}")
        return None, None
    except Exception as e:
        logger.exception(f"[moderation-client] Unexpected error when calling {url}: {e}")
        return None, None

def _truncate_preview(s: str, n: int = PREVIEW_LEN) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        try:
            s = json.dumps(s, ensure_ascii=False)
        except Exception:
            s = str(s)
    if len(s) <= n:
        return s
    return s[:n] + "..."

def _extract_clean_title_from_response(data):
    if not data:
        return None
    if isinstance(data, str):
        text = data.strip()
        if 3 <= len(text.split()) <= 40 and len(text) < 200:
            return text
        return None
    if isinstance(data, dict):
        for key in ("cleaned_text", "cleaned_title", "title", "cleaned", "headline"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                cand = val.strip()
                if len(cand) > 4 and len(cand.split()) < 200:
                    return cand
        if isinstance(data.get("title"), dict):
            tc = data.get("title")
            for key in ("cleaned_title", "cleaned"):
                val = tc.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        tc = data.get("title_cleanup") or data.get("moderation", {}).get("title_cleanup")
        if isinstance(tc, dict):
            for key in ("cleaned_title", "cleaned"):
                val = tc.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return None

async def _call_remote_moderation(session: aiohttp.ClientSession, title: str, body: str,
                                  timeout: int = 6, max_attempts: int = 2) -> Optional[str]:
    try_order = []
    if MODERATION_ARTICLE_URL:
        try_order.append(MODERATION_ARTICLE_URL)
    if MODERATION_TITLE_URL and MODERATION_TITLE_URL not in try_order:
        try_order.append(MODERATION_TITLE_URL)
    if not try_order:
        logger.warning("[moderation-client] No moderation endpoints configured")
        return None

    attempt = 0
    while attempt <= max_attempts:
        attempt += 1
        for url in try_order:
            if not url:
                continue
            logger.info(f"[moderation-client] Attempt {attempt} - calling {url}")
            if url.endswith("/moderate/article"):
                payload = {"original_title": title, "original_body": body}
            else:
                payload = {"text": title}

            status, data = await _post_json(session, url, payload, timeout=timeout)
            preview = _truncate_preview(data, PREVIEW_LEN)
            if status is None:
                logger.warning(f"[moderation-client] Network error when calling {url} (attempt {attempt})")
                continue

            logger.info(f"[moderation-client] {url} -> status={status} preview={preview!r}")

            if status == 200:
                cleaned = _extract_clean_title_from_response(data)
                if cleaned:
                    logger.info(f"[moderation-client] Extracted cleaned title from {url}: {cleaned!r}")
                    return cleaned
                else:
                    if isinstance(data, dict):
                        logger.warning(f"[moderation-client] 200 OK from {url} but no usable title; keys={list(data.keys())} preview={preview!r}")
                    else:
                        logger.warning(f"[moderation-client] 200 OK from {url} but response not JSON/object; preview={preview!r}")
            else:
                logger.warning(f"[moderation-client] Non-200 from {url}: {status} preview={preview!r}")

        if attempt <= max_attempts:
            backoff = min(2 ** attempt, 8)
            logger.info(f"[moderation-client] No usable response yet — backing off {backoff}s (attempt {attempt}/{max_attempts})")
            await asyncio.sleep(backoff)
    logger.warning("[moderation-client] All moderation attempts exhausted without usable result")
    return None

def _local_title_cleanup_fallback(text: str) -> str:
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        first = lines[0]
        first_clean = re.sub(r'(?im)^(?:revised|rewritten|revision|updated|here(?:\'s)?|note|update|original title|article title|headline|title)\b[^\n\r:]{0,120}[:\-\n\r]?', '', first).strip(' .,-–—•:')
        if len(first_clean.split()) >= 3 and not re.search(r'www\.|http|\d{4}', first_clean):
            return first_clean
    cleaned = text.strip()
    cleaned = re.sub(r'https?://\S+|\bwww\.\S+', '', cleaned)
    cleaned = re.sub(r'\[.*?\]', ' ', cleaned)
    cleaned = re.sub(r'(?im)^\s*(note:|update:).*$', ' ', cleaned, flags=re.M)
    cleaned = re.sub(r'["“”‘’\'\(\)\{\}]', '', cleaned)
    parts = re.split(r'\n|;|\||\t|—|–| - ', cleaned)
    parts = [p.strip(' .,-–—:•') for p in parts if p and len(p.strip()) >= 3]
    if parts:
        parts_sorted = sorted(parts, key=lambda x: abs(len(x.split()) - 10))
        best = parts_sorted[0]
        best = best.strip()
        if len(best.split()) > 18:
            best = ' '.join(best.split()[:18])
        return best
    final = re.sub(r'\s+', ' ', cleaned).strip(' .,-–—:')
    return final if len(final) >= 4 else "Untitled"

async def clean_title(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    can_resolve = False
    try:
        parsed = (MODERATION_ARTICLE_URL or MODERATION_TITLE_URL).split("://")[-1].split("/")[0]
        host = parsed.split(":")[0]
        socket.getaddrinfo(host, None)
        can_resolve = True
    except Exception:
        can_resolve = False

    if can_resolve:
        async with aiohttp.ClientSession() as session:
            try:
                cleaned = await _call_remote_moderation(session, text, text)
                if cleaned:
                    return cleaned
                else:
                    logger.warning("[moderation-client] Remote moderation returned no usable result, falling back to local heuristics")
            except Exception as e:
                logger.exception(f"[moderation-client] Unexpected exception during remote moderation: {e}")

    # Local agent fallback (attempt import)
    try:
        mod = __import__("moderation_service.agents", fromlist=["TitleModerationAgent"])
        TitleModerationAgent = getattr(mod, "TitleModerationAgent", None)
        if TitleModerationAgent:
            agent = TitleModerationAgent()
            if asyncio.iscoroutinefunction(agent.run):
                cleaned = await agent.run(text)
            else:
                loop = asyncio.get_event_loop()
                cleaned = await loop.run_in_executor(None, lambda: agent.run(text))
            if isinstance(cleaned, dict):
                for key in ("cleaned_title", "cleaned_text", "title"):
                    if key in cleaned and isinstance(cleaned[key], str) and cleaned[key].strip():
                        return cleaned[key].strip()
                return str(cleaned)
            elif isinstance(cleaned, str) and cleaned.strip():
                return cleaned.strip()
    except ModuleNotFoundError:
        logger.info("[moderation-client] Local TitleModerationAgent not found, using heuristic fallback.")
    except Exception as e:
        logger.exception(f"[moderation-client] Error running local TitleModerationAgent: {e}")

    return _local_title_cleanup_fallback(text)

# -------------------- DB --------------------

async def init_db(retries: int = 10, initial_backoff: float = 0.5):
    """
    Ensure Mongo is ready, then create index.
    Retries with exponential backoff.
    """
    backoff = initial_backoff
    for attempt in range(1, retries + 1):
        try:
            await wait_for_mongo(timeout=10, interval=1)
            # Ensure unique index on 'link'
            await collection.create_index("link", unique=True)
            # Ensure unique index on 'slug' for SEO-friendly URLs (sparse because older docs may lack slug)
            await collection.create_index("slug", unique=True, sparse=True)
            logger.info("[init_db] Indexes ensured on 'link' and 'slug'")
            return
        except Exception as e:
            logger.warning(f"[init_db] attempt {attempt}/{retries} failed: {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8.0)
    raise RuntimeError("[init_db] Could not initialize DB after retries")

# -------------------- Slug utilities --------------------

def _slugify(text: str, max_len: int = 100) -> str:
    """
    Create a URL-safe slug from text.
    Steps:
      - Normalize unicode to NFKD and remove diacritics
      - Keep letters/numbers and spaces/hyphens
      - Replace whitespace with single hyphen
      - Lowercase and trim
      - Truncate to max_len
    """
    if not text:
        return ""
    # Normalize unicode and remove diacritics
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Remove characters that are not letters, numbers, spaces, or hyphens
    cleaned = re.sub(r"[^\w\s-]", "", ascii_only, flags=re.UNICODE)
    # Convert spaces/underscores to single hyphen
    collapsed = re.sub(r"[\s_]+", "-", cleaned.strip())
    slug = collapsed.lower().strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    # fallback
    if not slug:
        return "article"
    return slug

async def _ensure_unique_slug(base_slug: str, link: str) -> str:
    """
    Ensure the slug is unique within the collection.
    If base_slug exists for a different link, append -1, -2 ... until unique.
    """
    candidate = base_slug
    suffix = 1
    while True:
        existing = await collection.find_one({"slug": candidate})
        if not existing:
            return candidate
        # If same link already has slug -> reuse it
        existing_link = existing.get("link") or existing.get("original_link")
        if existing_link == link:
            return candidate
        # otherwise try next suffix
        candidate = f"{base_slug}-{suffix}"
        suffix += 1

# -------------------- RSS Fetch --------------------

async def fetch_rss():
    print("🔄 Starting RSS fetch...")
    # No longer fire-and-forget wait_for_http_service here; startup wait is handled in init_db()

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

            # Parse publication date -> **store as field `published`** to match news_api
            try:
                pub_date = date_parser.parse(entry.get("published", "") or entry.get("pubDate", ""))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)

            raw_terms = [tag.get("term", "") for tag in entry.get("tags", [])]
            categories = map_to_global_categories(raw_terms)

            rewritten_title = None
            rewritten_body = None
            is_rewritten = False

            try:
                new_title, new_body = await rewrite_or_get_cached(link, raw_title, link)
                if new_body and not new_body.startswith(("[ERROR]", "[WARNING]")):
                    try:
                        cleaned_title = await clean_title(new_title if new_title else raw_title)
                    except Exception as e:
                        logger.exception(f"❌ Error during title cleaning fallback: {e}")
                        cleaned_title = new_title if new_title else raw_title

                    rewritten_title = cleaned_title.strip() if cleaned_title else None
                    rewritten_body = new_body.strip() if new_body else None
                    is_rewritten = True
                    print(f"✅ Rewritten & cleaned: {raw_title}")
                else:
                    print(f"⚠️ Rewrite returned empty/error for '{raw_title}'")
                    # Even if rewrite failed, still set titles so article can appear.
                    rewritten_title = None
                    rewritten_body = None
            except Exception as e:
                print(f"❌ [REWRITER] Failed to rewrite '{raw_title}': {e}")
                rewritten_title = None
                rewritten_body = None

            # Choose title for slug: prefer rewritten_title (if present), else original title
            title_for_slug = (rewritten_title or raw_title or "").strip()
            base_slug = _slugify(title_for_slug)
            # ensure unique slug
            try:
                unique_slug = await _ensure_unique_slug(base_slug, link)
            except Exception as e:
                logger.warning(f"[slug] Failed to ensure unique slug for '{base_slug}': {e}")
                unique_slug = base_slug

            doc = {
                "link": link,
                "original_link": link,
                "original_title": raw_title,
                "rewritten_title": rewritten_title,
                "original_body": None,
                "rewritten_body": rewritten_body,
                "categories": categories,
                "is_rewritten": is_rewritten,
                "fetched_at": datetime.now(timezone.utc),
                # store as `published` to be compatible with news_api/db.py sorting
                "published": pub_date,
                "slug": unique_slug
            }

            try:
                await collection.update_one({"link": link}, {"$set": doc}, upsert=True)
            except Exception as e:
                print(f"❌ DB insert error for '{link}': {e}")
