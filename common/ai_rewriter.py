import os
import asyncio
import logging
import json
import re
import aiohttp
import traceback
from typing import Tuple, Optional

from llama_cpp import Llama
from newspaper import Article
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

# === Configuration ===
MODEL_PATH = os.getenv(
    "LLAMA_MODEL_PATH",
    os.path.expanduser("~/llama.cpp/models/llama-3-3b/Llama-3.2-3B-Instruct-Q4_K_M.gguf")
)
NUM_THREADS = int(os.getenv("LLAMA_NUM_THREADS", "4"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rss_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "news")
MODERATION_SERVICE_URL = os.getenv("MODERATION_SERVICE_URL", "http://moderation_service:8002")
# How many attempts to call moderation service (increased default so fetcher waits longer)
MODERATION_MAX_ATTEMPTS = int(os.getenv("MODERATION_MAX_ATTEMPTS", "5"))
MODERATION_INITIAL_BACKOFF = float(os.getenv("MODERATION_INITIAL_BACKOFF", "1.0"))

# Local fallback relaxed thresholds (less censoring)
LOCAL_TITLE_MIN_LEN = int(os.getenv("LOCAL_TITLE_MIN_LEN", "15"))
LOCAL_BODY_MIN_LEN = int(os.getenv("LOCAL_BODY_MIN_LEN", "120"))

# === Logger ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ai_rewriter")

# === Try to load the LLaMA model once ===
llm = None
llm_lock = asyncio.Lock()

try:
    logger.info(f"Attempting to load LLaMA model from: {MODEL_PATH} with {NUM_THREADS} threads")
    llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=NUM_THREADS, verbose=False)
    logger.info("LLaMA model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load LLaMA model at {MODEL_PATH}: {e}")
    llm = None

# === Database client ===
client = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

# === Moderation Service Client (robust) ===
async def call_moderation_service(endpoint: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    """
    Robust call with retries and backoff.
    endpoint may be "moderate/article" or "moderate/title" (with or without leading slash).
    Returns parsed JSON dict on success, or None.
    """
    base = (MODERATION_SERVICE_URL or "").rstrip("/")
    ep = endpoint.lstrip("/")
    url = f"{base}/{ep}"

    attempt = 0
    backoff = MODERATION_INITIAL_BACKOFF
    while attempt < MODERATION_MAX_ATTEMPTS:
        attempt += 1
        try:
            logger.info(f"[moderation-client] Attempt {attempt} - calling {url}")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=timeout) as resp:
                    status = resp.status
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = None

                    logger.info(f"[moderation-client] {url} -> status={status} preview={text[:1000]!r}")
                    if status == 200:
                        if data:
                            return data
                        else:
                            logger.warning(f"[moderation-client] 200 OK but response not JSON from {url}; preview={text[:1000]!r}")
                            return None
                    else:
                        logger.warning(f"[moderation-client] Non-200 from {url}: {status} preview={text[:1000]!r}")
        except asyncio.TimeoutError:
            logger.warning(f"[moderation-client] Timeout when calling {url} (attempt {attempt})")
        except aiohttp.ClientConnectorError as e:
            logger.warning(f"[moderation-client] Connector error to {url}: {e} (attempt {attempt})")
        except Exception as e:
            logger.exception(f"[moderation-client] Unexpected error when calling {url}: {e} (attempt {attempt})")

        if attempt < MODERATION_MAX_ATTEMPTS:
            logger.info(f"[moderation-client] Backing off {backoff}s before next moderation attempt")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8.0)

    logger.warning("[moderation-client] All moderation attempts exhausted without usable result")
    return None

# === Improved Title Cleaning ===
def clean_title_locally(title: str, min_len=30, max_len=90) -> str:
    if not title:
        return ""
    patterns_to_remove = [
        r'(?i)^(here\'?s?\s+the\s+)?rewritten\s+(article|title|version)[:.\s]*',
        r'(?i)^(revised|updated|cleaned|modified)\s+(title|article|version)[:.\s]*',
        r'(?i)^title[:.\s]+',
        r'(?i)^headline[:.\s]+',
        r'(?i)^article\s+title[:.\s]+',
        r'(?i)^original\s+article[:.\s]*',
        r'(?i)^note[:.\s]+.*?[\n\r]',
        r'^\s*[\"""\'\']+\s*',
        r'\s*[\"""\'\']+\s*$',
        r'^\s*[-–—•]\s+',
    ]
    cleaned = title.strip()
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.I | re.M)
    cleaned = re.sub(r'^\s*\w+\s+\d{1,2},\s*\d{4}\s*[•\-\|]?\s*', '', cleaned)
    cleaned = re.sub(r'\s*[•\-\|]\s*www\.\S+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_len:
        cut_idx = cleaned.rfind(' ', 0, max_len)
        if cut_idx > 0:
            cleaned = cleaned[:cut_idx].strip()
        else:
            cleaned = cleaned[:max_len]
    cleaned = re.sub(r'[,:;]+$', '', cleaned)
    return cleaned if len(cleaned) >= 10 else ""

# === Better JSON extraction ===
def extract_json_from_llm_output(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    try:
        data = json.loads(text.strip())
        title = data.get("title", "").strip()
        body = data.get("body", "").strip()
        if title and body:
            return title, body
    except Exception:
        pass
    json_pattern = r'\{[^{}]*"title"[^{}]*"body"[^{}]*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match)
            title = data.get("title", "").strip()
            body = data.get("body", "").strip()
            if title and body:
                return title, body
        except Exception:
            continue
    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
    body_match = re.search(r'"body"\s*:\s*"([^"]+(?:\\.[^"]+)*)"', text, re.DOTALL)
    if title_match and body_match:
        title = title_match.group(1).strip()
        body = body_match.group(1).strip()
        body = body.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        return title, body
    label_title = re.search(r'(?m)^\s*Title\s*[:\-]\s*(.+)$', text)
    label_body = re.search(r'(?ms)^\s*Body\s*[:\-]\s*(.+)$', text)
    if label_title and label_body:
        t = label_title.group(1).strip()
        b = label_body.group(1).strip()
        return t, b
    return None, None

# === Background DB saver helper ===
async def _save_article_background(link: str, payload: dict):
    try:
        await collection.update_one({"link": link}, {"$set": payload}, upsert=True)
        logger.info(f"[REWRITER-DB] Background saved article link={link}")
    except Exception as e:
        logger.warning(f"[REWRITER-DB] Background DB save failed for link={link}: {e}")

# === Main rewrite function ===
async def rewrite_or_get_cached(link: str, original_title: str, url: str) -> tuple[str, str]:
    if llm is None:
        logger.warning("LLM not initialized, skipping rewrite")
        return original_title, ""

    # Try cache
    try:
        cached = await collection.find_one({
            "link": link,
            "is_rewritten": True,
            "rewrite_status": "complete",
            "moderation_passed": True
        })
        if cached:
            rewritten_title = cached.get("rewritten_title", "").strip()
            rewritten_body = cached.get("rewritten_body", "").strip()
            if rewritten_title and rewritten_body:
                logger.info(f"[REWRITER] Returning cached moderated article for link={link}")
                return rewritten_title, rewritten_body
    except Exception as e:
        logger.warning(f"[REWRITER] Failed to check cache: {e}")

    # Mark present (best-effort)
    try:
        await collection.update_one(
            {"link": link},
            {"$setOnInsert": {"is_rewritten": False, "moderation_passed": False}},
            upsert=True
        )
    except Exception:
        pass

    # Fetch article
    try:
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text or ""
        logger.info(f"[REWRITER] Fetched article, len={len(full_text)} for url={url}")
    except Exception as e:
        error_msg = f"[ERROR] Unable to fetch article: {e}"
        logger.error(f"[REWRITER] {error_msg}")
        return original_title, error_msg

    if not full_text.strip() or len(full_text) < 100:
        warning_msg = "[WARNING] Article too short or empty"
        logger.warning(f"[REWRITER] {warning_msg} for URL={url}")
        return original_title, warning_msg

    system_prompt = """You are a professional news editor. Your task is to rewrite articles in clean, journalistic style.

CRITICAL RULES:
1. Output ONLY valid JSON with exactly two keys: "title" and "body"
2. DO NOT include ANY meta-commentary
3. DO NOT include dates, sources, or website names in the title
4. The title must be a single, compelling headline (40-90 characters)
5. The body must be the complete article text, ending with proper punctuation
6. Write in third person, professional news style
7. Preserve ALL key facts and quotes from the original
"""
    article_prompt = f"""Rewrite this article as clean JSON with "title" and "body" keys.

Article to rewrite:
{full_text[:1500]}

Remember: Output ONLY the JSON object, no other text."""
    max_attempts = 4
    best_title = None
    best_body = None
    moderation_passed = False
    moderation_result = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with llm_lock:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: llm(
                        f"{system_prompt}\n\n{article_prompt}",
                        max_tokens=2048,
                        temperature=0.3,
                        stop=["</s>", "\n\n\n"]
                    )
                )
                raw_output = response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"[REWRITER] LLM call failed on attempt {attempt}: {e}")
            logger.debug(traceback.format_exc())
            continue

        logger.debug(f"[REWRITER] LLM output attempt {attempt}: {raw_output[:500]}")
        title, body = extract_json_from_llm_output(raw_output)

        if not title or not body:
            logger.warning(f"[REWRITER] Failed to extract JSON on attempt {attempt}")
            continue

        title = clean_title_locally(title)
        body = re.sub(r'^(?:Original article:|Note:|Here\'s the rewritten.*?:)\s*', '', body, flags=re.I).strip()

        if not body or len(body) < 100:
            logger.warning(f"[REWRITER] Body too short on attempt {attempt}")
            continue

        if not body[-1] in '.!?':
            if len(body) >= 200:
                body = body + "."
                logger.debug(f"[REWRITER] Appended period to body on attempt {attempt}")
            else:
                logger.warning(f"[REWRITER] Body doesn't end with proper punctuation on attempt {attempt}")
                continue

        # Call moderation service with retries/backoff
        moderation_result = await call_moderation_service(
            "moderate/article",
            {
                "original_title": original_title,
                "original_body": full_text[:1000],
                "rewritten_title": title,
                "rewritten_body": body
            },
            timeout=10
        )

        if moderation_result:
            try:
                mr_preview = json.dumps(moderation_result, ensure_ascii=False)[:2000]
            except Exception:
                mr_preview = str(moderation_result)[:2000]
            logger.debug(f"[REWRITER] moderation_result preview: {mr_preview!r}")

            if moderation_result.get("final_decision", False):
                title_data = moderation_result.get("title", {})
                cleaned_title = title_data.get("cleaned_title", title)
                content_data = moderation_result.get("content", {})
                if content_data.get("final_decision", False):
                    best_title = cleaned_title
                    best_body = body
                    moderation_passed = True
                    logger.info(f"[REWRITER] Article passed moderation on attempt {attempt}")
                    break
                else:
                    # Log explicit reasons why content failed
                    logger.warning(f"[REWRITER] Content moderation returned final_decision=False on attempt {attempt}. content={json.dumps(content_data, ensure_ascii=False)[:1000]!r}")
            else:
                logger.warning(f"[REWRITER] Moderation returned final_decision=False on attempt {attempt}. full_preview={mr_preview!r}")
        else:
            logger.warning(f"[REWRITER] Moderation service unavailable or returned non-JSON (attempt {attempt})")

        logger.info(f"[REWRITER] Moderation failed on attempt {attempt}")

    # Local fallback policy (more permissive)
    if not best_body:
        # If remote unavailable entirely, accept local validated result with relaxed thresholds
        if (not moderation_result) and title and body and len(title) >= LOCAL_TITLE_MIN_LEN and len(body) >= LOCAL_BODY_MIN_LEN and body[-1] in '.!?':
            best_title = title
            best_body = body
            moderation_passed = False
            logger.info("[REWRITER] Using local-validated rewrite (remote moderation unavailable)")
        else:
            logger.info("[REWRITER] No acceptable rewrite found after attempts")

    final_title = best_title or clean_title_locally(original_title)
    final_body = best_body or ""
    rewrite_status = "complete" if final_body else "failed"

    payload = {
        "rewritten_title": final_title,
        "rewritten_body": final_body,
        "is_rewritten": bool(final_body),
        "rewrite_status": rewrite_status,
        "moderation_passed": moderation_passed,
        "original_title": original_title,
        "original_link": url
    }
    try:
        asyncio.create_task(_save_article_background(link, payload))
    except Exception as e:
        logger.warning(f"[REWRITER] Could not schedule DB save task: {e}")

    logger.info(f"[REWRITER] Saved article: status={rewrite_status}, moderated={moderation_passed} (background)")
    return final_title, final_body if final_body else ""
