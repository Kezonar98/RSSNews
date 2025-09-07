# tests/test_ai_rewriter.py
import pytest
import asyncio
import re
from common import ai_rewriter


@pytest.mark.asyncio
async def test_rewrite_or_get_cached(monkeypatch):
    """Test rewriting logic and caching behavior."""

    # Fake LLM response
    def fake_llm(prompt, max_tokens=800, temperature=0.7):
        return {
            "choices": [{
                "text": "Title: Global Markets Face Uncertainty\nBody: Investors remain cautious amid economic slowdown."
            }]
        }

    monkeypatch.setattr(ai_rewriter, "llm", fake_llm)

    link = "http://example.com/article1"
    title = "Rewritten: Markets struggle with new challenges"
    body = "Original article: Click here for more details https://spam.com"

    # === First run (should rewrite and save to cache) ===
    rewritten_title, rewritten_body = await ai_rewriter.rewrite_or_get_cached(link, title, body)

    assert rewritten_title != "" and "rewritten" not in rewritten_title.lower()
    assert rewritten_body != "" and not re.search(r"https?://", rewritten_body)
    assert "click here" not in rewritten_body.lower()

    # === Second run (should load from cache, not call llm again) ===
    monkeypatch.setattr(ai_rewriter, "llm", lambda *a, **k: {"choices": [{"text": "SHOULD NOT BE CALLED"}]})

    cached_title, cached_body = await ai_rewriter.rewrite_or_get_cached(link, title, body)

    assert cached_title == rewritten_title
    assert cached_body == rewritten_body
