import pytest
from fastapi.testclient import TestClient
from moderation_service.main import app

client = TestClient(app)

def test_moderate_title_api():
    text = "Rewritten title: Sample headline for testing"
    response = client.post("/moderate/title", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert "Sample headline for testing" in data["cleaned_title"]

def test_moderate_article_api():
    req = {
        "original_title": "Original title example",
        "original_body": "Some body text",
        "rewritten_title": "Rewritten title example",
        "rewritten_body": "Rewritten body text"
    }
    response = client.post("/moderate/article", json=req)
    assert response.status_code == 200
    data = response.json()
    # Check that title cleanup and content moderation results exist
    assert "title" in data
    assert "content" in data
    assert "cleaned_title" in data["title"]
