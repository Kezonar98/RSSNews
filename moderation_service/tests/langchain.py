"""
Integration tests for local moderation agents.

This script checks:
1. Detoxify toxic content detection
2. HuggingFace pipeline
3. LangChain HuggingFacePipeline wrapper
4. FastAPI endpoint (moderation_agent)

Run:
    python integration_test.py
"""

import requests
from detoxify import Detoxify
from transformers import pipeline
from langchain_huggingface import HuggingFacePipeline


# === 1. Detoxify ===
def test_detoxify():
    print("\n=== TEST 1: Detoxify ===")
    model = Detoxify('original')
    texts = ["I love programming!", "You are so stupid!"]
    for t in texts:
        result = model.predict(t)
        print(f"Text: {t}")
        print("Prediction:", result)


# === 2. HuggingFace Pipeline ===
def test_hf_pipeline():
    print("\n=== TEST 2: HuggingFace Pipeline ===")
    classifier = pipeline("text-classification", model="unitary/toxic-bert")
    texts = ["You are awesome!", "You are stupid!"]
    for t in texts:
        result = classifier(t)
        print(f"Text: {t}")
        print("Prediction:", result)


# === 3. LangChain HuggingFacePipeline ===
def test_langchain_wrapper():
    print("\n=== TEST 3: LangChain HuggingFacePipeline ===")
    classifier = pipeline("text-classification", model="unitary/toxic-bert")
    hf = HuggingFacePipeline(pipeline=classifier)
    texts = ["Have a nice day!", "You are disgusting!"]
    for t in texts:
        result = hf.invoke(t)
        print(f"Text: {t}")
        print("Prediction:", result)


# === 4. FastAPI endpoint test ===
def test_fastapi_endpoint():
    print("\n=== TEST 4: FastAPI Endpoint ===")
    url = "http://127.0.0.1:8000/moderate"  # твій endpoint
    texts = ["Good morning!", "You idiot!"]

    for t in texts:
        try:
            response = requests.post(url, json=t, timeout=5)
            if response.status_code == 200:
                print(f"Text: {t}")
                print("Response:", response.json())
            else:
                print(f"Error {response.status_code} -> {response.text}")
        except Exception as e:
            print("⚠️ Could not reach FastAPI server. Did you start `uvicorn main:app --reload`?")
            print(e)


if __name__ == "__main__":
    test_detoxify()
    test_hf_pipeline()
    test_langchain_wrapper()
    test_fastapi_endpoint()
