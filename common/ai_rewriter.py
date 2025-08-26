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

# === Utility ===
def clean_and_trim_title(title: str, min_len=40, max_len=90) -> str:
    """
    Ensure title is clean, not cut mid-word, and SEO-friendly length.
    """
    title = title.replace("\n", " ").strip()
    # Remove error markers
    for bad in ["[ERROR]", "[WARNING]"]:
        title = title.replace(bad, "")

    # If too long -> trim at last space before max_len
    if len(title) > max_len:
        cut_idx = title.rfind(" ", 0, max_len)
        if cut_idx == -1:
            cut_idx = max_len
        title = title[:cut_idx].strip()

    # If too short -> fallback to original length
    if len(title) < min_len:
        logger.warning(f"[REWRITER] Title too short after trimming: '{title}'")
    return title


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
            {"link": link, "is_rewritten": True}
        )
        if cached:
            rewritten_title = cached.get("rewritten_title", "").strip()
            rewritten_body = cached.get("rewritten_body", "").strip()
            if rewritten_title and rewritten_body and not rewritten_body.startswith(("[ERROR]", "[WARNING]")):
                return rewritten_title, rewritten_body
    except Exception as e:
        logger.warning(f"[REWRITER] Failed to check cache: {e}")

    # Prevent duplicate race-condition rewrites
    try:
        await collection.update_one(
            {"link": link},
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

    # === SEO-friendly prompts ===
    title_prompt = (
        f"Rewrite this news title in professional journalistic style. "
        f"It must be clear, complete, and SEO-friendly (40–90 characters). "
        f"Do not cut words, do not leave it unfinished, do not add clickbait.\n\n"
        f"Original title: {original_title}"
    )

    body_prompt = (
        "Rewrite the following news article in a professional, concise and SEO-friendly journalistic style. "
        "Keep facts accurate, do not invent anything. Make it smooth, well-structured, and engaging. "
        "Length should be natural for an online news article.\n\n"
        f"Article text:\n{full_text}\n\n"
    )

    async with llm_lock:
        new_title = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm(title_prompt, max_tokens=96, stop=["</s>"])["choices"][0]["text"].strip()
        )
        new_body = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm(body_prompt, max_tokens=1024, stop=["</s>"])["choices"][0]["text"].strip()
        )

    # Clean & enforce SEO rules on title
    new_title = clean_and_trim_title(new_title)

    # Always append original source
    new_body = f"{new_body}\n\nOriginal article: {url}"

    # Save to DB
    try:
        await collection.update_one(
            {"link": link},
            {"$set": {
                "rewritten_title": new_title,
                "rewritten_body": new_body,
                "is_rewritten": True
            }}
        )
    except Exception as e:
        logger.error(f"[REWRITER] Failed to save rewritten data: {e}")

    return new_title, new_body
