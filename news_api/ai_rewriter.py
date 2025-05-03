# news_api/ai_rewriter.py  (або скопіюй цей файл також в rss_fetcher/)
import os
import aiohttp
from newspaper import Article

HF_API_KEY   = os.getenv("HF_API_KEY")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/google/flan-t5-small"
MAX_CHARS    = 8000

def split_chunks(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    # ... (твоя існуюча реалізація)
    chunks, current = [], ""
    for para in text.split("\n\n"):
        block = para.strip()
        if not block: continue
        if len(current) + len(block) > max_chars:
            chunks.append(current); current = block
        else:
            current = (current + "\n\n" + block).strip()
    if current: chunks.append(current)
    return chunks

async def rewrite_text(original_title: str, url: str) -> tuple[str, str]:
    """
    Завантажує повний текст (через newspaper3k) і рерайтить заголовок та тіло.
    Повертає (rewritten_title, rewritten_body).
    """
    # 1. Парсимо статтю
    article = Article(url)
    article.download(); article.parse()
    full_text = article.text

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        # заголовок
        async with session.post(
            HF_MODEL_URL, json={"inputs": f"Rewrite the title: {original_title}"}, headers=headers
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            new_title = data[0].get("generated_text", original_title)

        # тіло паралельно
        chunks = split_chunks(full_text)
        tasks = [session.post(HF_MODEL_URL, json={"inputs": c}, headers=headers) for c in chunks]
        responses = await asyncio.gather(*tasks)
        parts = []
        for r in responses:
            r.raise_for_status()
            out = await r.json()
            parts.append(out[0].get("generated_text", ""))

        new_body = "\n\n".join(parts)
        # додаємо посилання на оригінал
        new_body += f"\n\nOriginal article: {url}"

    return new_title, new_body
