# common/ai_rewriter.py
import os
import asyncio
import logging
from bson import ObjectId
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

# === Logger ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# === Try to load the LLaMA model once ===
llm = None
llm_lock = asyncio.Lock()  # Lock to avoid concurrent LLaMA calls

try:
    logger.info(f"Attempting to load LLaMA model from: {MODEL_PATH} with {NUM_THREADS} threads")
    llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=NUM_THREADS, verbose=False)
    logger.info("LLaMA model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load LLaMA model at {MODEL_PATH}: {e}")

# === Database client ===
client = AsyncIOMotorClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]


# === Functions ===

async def rewrite_or_get_cached(link: str, original_title: str, url: str) -> tuple[str, str]:
    """
    Paraphrase with caching (for news_api).
    If LLM is unavailable, returns original data unchanged.
    
    """
    if llm is None:
        logger.warning("LLM not initialized, skipping rewrite_or_get_cached")
        return original_title, ""

    # Try returning cached result if valid
    try:
        cached = await collection.find_one(
            {"link": link, "is_rewritten": True}  # Find by link instead of ObjectId(news_id)
        )
        if cached:
            rewritten_title = cached.get("rewritten_title", "").strip()
            rewritten_body = cached.get("rewritten_body", "").strip()
            if rewritten_title and rewritten_body and not rewritten_body.startswith(("[ERROR]", "[WARNING]")):
                return rewritten_title, rewritten_body
    except Exception as e:
        logger.warning(f"[REWRITER] Failed to check cache: {e}")

    # Avoid duplicate race-condition rewrites (set default flag)
    try:
        await collection.update_one(
            {"link": link},  # Update by link
            {"$setOnInsert": {"is_rewritten": False}},
            upsert=True,
        )
    except DuplicateKeyError:
        pass

    # Fetch article text
    try:
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text or ""
        logger.info(f"[REWRITER] Fetched article, len={len(full_text)}")
    except Exception as e:
        error_msg = f"[ERROR] Unable to fetch or parse article: {e}"
        logger.error(f"[REWRITER] {error_msg}")
        return original_title, error_msg

    if not full_text.strip():
        warning_msg = "[WARNING] Empty article text"
        logger.warning(f"[REWRITER] {warning_msg} for URL={url}")
        return original_title, warning_msg

    title_prompt = f"Paraphrase this title for a news website:\n\n{original_title}"
    body_prompt = (
        "Paraphrase the following news article text to make it concise and engaging:\n\nDon't add any new information, just rewrite the text.\n\n"
        f"{full_text}\n\n"
    )

    async with llm_lock:
        new_title = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm(title_prompt, max_tokens=64, stop=["</s>"])["choices"][0]["text"].strip()
        )
        new_body = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm(body_prompt, max_tokens=512, stop=["</s>"])["choices"][0]["text"].strip()
        )

    new_body = f"{new_body}\n\nOriginal article: {url}"

    try:
        await collection.update_one(
            {"link": link},  # Update by link
            {"$set": {
                "rewritten_title": new_title,
                "rewritten_body": new_body,
                "is_rewritten": True
            }}
        )
    except Exception as e:
        logger.error(f"[REWRITER] Failed to save rewritten data: {e}")

    return new_title, new_body
