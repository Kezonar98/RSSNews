from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio

from .agents import (
    TitleCleanupAgent,
    QuotedTitleAgent,
    ToxicityAgent,
    SafeContentAgent,
    DuplicateCheckerAgent,
    ContextValidatorAgent,
)
from . import config

app = FastAPI(title="Moderation Service")

# ---------- Schemas ----------

class TextRequest(BaseModel):
    text: str

class TitleResponse(BaseModel):
    original: str
    cleaned_title: str
    candidates: Optional[List[str]] = None

class ContentModerationResponse(BaseModel):
    toxicity: Dict[str, Any]
    safety: Dict[str, Any]
    duplicates: Dict[str, Any]
    final_decision: bool

class ArticleModerationRequest(BaseModel):
    original_title: Optional[str] = None
    original_body: Optional[str] = None
    rewritten_title: Optional[str] = None
    rewritten_body: Optional[str] = None

class ArticleModerationResponse(BaseModel):
    title: TitleResponse
    content: ContentModerationResponse
    context: Dict[str, Any]
    final_decision: bool

# ---------- Instantiate agents once ----------
title_agent = TitleCleanupAgent()
quoted_agent = QuotedTitleAgent()
tox_agent = ToxicityAgent()
safe_agent = SafeContentAgent()
dup_agent = DuplicateCheckerAgent()
ctx_agent = ContextValidatorAgent()

# ---------- Helpers ----------

async def _run_agent(agent_fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: agent_fn(*args, **kwargs))

def _final_decision(*flags: bool) -> bool:
    """
    Compute final decision.
    If ALLOW_ALL is set in config, always allow.
    """
    if getattr(config, "ALLOW_ALL", False):
        return True
    return all(flags)

# ---------- Endpoints ----------

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/moderate/title", response_model=TitleResponse)
async def moderate_title(req: TextRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    quoted_res = await _run_agent(quoted_agent.run, text)
    fallback_res = await _run_agent(title_agent.run, text)

    # Prefer quoted extraction if acceptable
    prefer = quoted_res.get("cleaned_title")
    if prefer and len(prefer.split()) >= config.MIN_TITLE_WORDS:
        final = prefer.strip()
        cands = quoted_res.get("candidates") or []
        fb = fallback_res.get("cleaned_title")
        if fb and fb not in cands:
            cands.append(fb)
    else:
        final = (fallback_res.get("cleaned_title") or text).strip()
        cands = fallback_res.get("candidates") or None

    return {
        "original": text,
        "cleaned_title": final,
        "candidates": cands or None
    }

@app.post("/moderate/content", response_model=ContentModerationResponse)
async def moderate_content(req: TextRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    tox_task = asyncio.create_task(_run_agent(tox_agent.run, text))
    safe_task = asyncio.create_task(_run_agent(safe_agent.run, text))
    dup_task  = asyncio.create_task(_run_agent(dup_agent.run, text))

    tox_res, safe_res, dup_res = await asyncio.gather(tox_task, safe_task, dup_task)

    # Base decision: safety + duplicate checks (previous behavior)
    decision = _final_decision(
        safe_res.get("safe", False),
        dup_res.get("ok", True)
    )

    # If ALLOW_ALL is enabled, override final decision to True and normalize flags
    if getattr(config, "ALLOW_ALL", False):
        decision = True
        # ensure safety/duplicates reflect permissive outcome for downstream consumers
        if isinstance(safe_res, dict):
            safe_res = {**safe_res, "safe": True}
        if isinstance(dup_res, dict):
            dup_res = {**dup_res, "ok": True}

    return {
        "toxicity": tox_res,
        "safety": safe_res,
        "duplicates": dup_res,
        "final_decision": decision
    }

@app.post("/moderate/article", response_model=ArticleModerationResponse)
async def moderate_article(req: ArticleModerationRequest):
    """
    Full article moderation:
      - Title cleanup (use rewritten_title if present)
      - Content checks on rewritten_body or original_body
      - Context check between original and rewritten
    """
    # Title
    title_input = req.rewritten_title or req.original_title or ""
    if not title_input.strip():
        raise HTTPException(status_code=400, detail="Missing title text")

    title_res = await moderate_title(TextRequest(text=title_input))

    # Content
    content_input = (req.rewritten_body or req.original_body or "").strip()
    if not content_input:
        raise HTTPException(status_code=400, detail="Missing article body")
    content_res = await moderate_content(TextRequest(text=content_input))

    # Context check (prefer body-to-body)
    if req.original_body and req.rewritten_body:
        ctx_res = await _run_agent(ctx_agent.run, req.original_body, req.rewritten_body)
    elif req.original_title and req.rewritten_title:
        ctx_res = await _run_agent(ctx_agent.run, req.original_title, req.rewritten_title)
    else:
        ctx_res = {"keywords": [], "present": [], "coverage": 1.0, "ok": True}

    # Final decision combines content decision and context
    final = _final_decision(content_res["final_decision"], ctx_res.get("ok", True))

    # If ALLOW_ALL is enabled, force final decision and normalize context/content flags
    if getattr(config, "ALLOW_ALL", False):
        final = True
        if isinstance(ctx_res, dict):
            ctx_res = {**ctx_res, "ok": True}
        if isinstance(content_res, dict):
            content_res = {**content_res, "final_decision": True}

    return {
        "title": title_res,
        "content": content_res,
        "context": ctx_res,
        "final_decision": final
    }

# Back-compat combined endpoint (applies to a single text blob)
@app.post("/moderate", response_model=dict)
async def moderate_both(req: TextRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    title_res = await moderate_title(TextRequest(text=text))
    content_res = await moderate_content(TextRequest(text=text))
    return {"title_cleanup": title_res, "content_moderation": content_res}
