# moderation_service/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import asyncio

# Import agents from local module
# Agents should return JSON-serializable values (floats converted already in agents.py)
from agents import TitleCleanupAgent, QuotedTitleAgent, ToxicityAgent, SafeContentAgent

app = FastAPI(title="Moderation Service")

# Pydantic models for requests/responses
class TextRequest(BaseModel):
    text: str

class TitleResponse(BaseModel):
    original: str
    cleaned_title: str
    candidates: list[str] | None = None

class ContentModerationResponse(BaseModel):
    toxicity: Dict[str, float]
    safety: Dict[str, Any]

# Instantiate agents once (models loaded on first instantiation)
# Note: instantiation may load models/checkpoints (heavy). Ensure model files are pre-cached or container has network.
title_agent = TitleCleanupAgent()
quoted_agent = QuotedTitleAgent()
tox_agent = ToxicityAgent()
safe_agent = SafeContentAgent()

# Helper to run possibly blocking agent.run in executor if synchronous
async def _run_agent(agent, text: str):
    if asyncio.iscoroutinefunction(agent.run):
        return await agent.run(text)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: agent.run(text))

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}

@app.post("/moderate/title", response_model=TitleResponse)
async def moderate_title(req: TextRequest):
    """
    Clean and normalize a news title.
    Tries quoted extraction and fallback cleanup; returns cleaned title + candidates.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    # Prefer quoted extraction first (if present)
    quoted_res = await _run_agent(quoted_agent, text)
    cleaned_quoted = quoted_res.get("cleaned_title") if isinstance(quoted_res, dict) else None

    # Always also compute fallback title cleanup for audit
    fallback_res = await _run_agent(title_agent, text)
    cleaned_fallback = fallback_res.get("cleaned_title") if isinstance(fallback_res, dict) else None

    # Decide final cleaned title: prefer quoted result if it looks reasonable
    final = None
    candidates = []
    if cleaned_quoted and isinstance(cleaned_quoted, str) and len(cleaned_quoted.split()) >= 3:
        final = cleaned_quoted.strip()
        # collect candidates for response
        cand_list = quoted_res.get("candidates") if isinstance(quoted_res, dict) else []
        if cand_list:
            candidates.extend(cand_list)
    if cleaned_fallback and cleaned_fallback not in candidates:
        candidates.append(cleaned_fallback)

    if not final:
        # fallback to best from fallback agent
        final = cleaned_fallback or (text if len(text) < 200 else text[:200])

    return {
        "original": text,
        "cleaned_title": final,
        "candidates": candidates or None
    }

@app.post("/moderate/content", response_model=ContentModerationResponse)
async def moderate_content(req: TextRequest):
    """
    Moderate article body: run toxicity and safe-content checks.
    Returns numeric toxicity scores and safety info.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    # Run toxicity and safety agents (possibly heavy) concurrently
    tox_task = asyncio.create_task(_run_agent(tox_agent, text))
    safe_task = asyncio.create_task(_run_agent(safe_agent, text))

    tox_res = await tox_task
    safe_res = await safe_task

    # Ensure types are JSON serializable (agents should return primitives)
    return {
        "toxicity": tox_res if isinstance(tox_res, dict) else {"score": tox_res},
        "safety": safe_res if isinstance(safe_res, dict) else {"safe": bool(safe_res)}
    }

# Optional combined endpoint for convenience
@app.post("/moderate", response_model=dict)
async def moderate_both(req: TextRequest):
    """
    Convenience endpoint: returns title cleanup + content moderation.
    Useful when caller provides full article text (title+body combined).
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    title_res = await moderate_title(TextRequest(text=text))
    content_res = await moderate_content(TextRequest(text=text))
    return {
        "title_cleanup": title_res,
        "content_moderation": content_res
    }
