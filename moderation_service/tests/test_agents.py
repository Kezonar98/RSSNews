import pytest
from moderation_service.agents import (
    ToxicityAgent,
    SafeContentAgent,
    TitleCleanupAgent,
    QuotedTitleAgent,
    DuplicateCheckerAgent,
    ContextValidatorAgent
)

# --------------------- TOXICITY ---------------------
def test_toxicity_agent():
    agent = ToxicityAgent()
    result = agent.run("You are an idiot!")
    assert "toxicity" in result
    assert "model_loaded" in result
    # fallback case
    agent._ready = False
    fallback = agent.run("Hello world")
    assert fallback["toxicity"] == 0.0
    assert fallback["model_loaded"] is False

# --------------------- SAFE CONTENT ---------------------
def test_safe_content_agent():
    agent = SafeContentAgent()
    safe = agent.run("This is a clean sentence.")
    assert safe["safe"] is True
    unsafe = agent.run("kill all humans")
    assert unsafe["safe"] is False

# --------------------- TITLE CLEANUP ---------------------
def test_title_cleanup_agent():
    agent = TitleCleanupAgent()
    text = "Updated: Breaking news: Something happened today"
    res = agent.run(text)
    assert res["cleaned_title"] != ""
    assert res["original"] == text
    assert isinstance(res["candidates"], list)

# --------------------- QUOTED TITLE ---------------------
def test_quoted_title_agent():
    agent = QuotedTitleAgent()
    text = 'He said "This is the real title" and continued.'
    res = agent.run(text)
    assert "cleaned_title" in res
    assert res["cleaned_title"] == "This is the real title"

# --------------------- DUPLICATE CHECKER ---------------------
def test_duplicate_checker_agent():
    agent = DuplicateCheckerAgent()
    text = "Sentence one. Sentence two. Sentence one."
    res = agent.run(text)
    assert "duplicate_ratio" in res
    assert res["duplicates"] == 1
    assert res["ok"] is False

# --------------------- CONTEXT VALIDATOR ---------------------
def test_context_validator_agent():
    agent = ContextValidatorAgent()
    original = "Python is a programming language. It is popular."
    rewritten = "Python is a popular programming language."
    res = agent.run(original, rewritten)
    assert "coverage" in res
    assert "ok" in res
    assert res["ok"] is True
