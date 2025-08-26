import re

def clean_text(text: str) -> str:
    """Remove extra spaces, normalize"""
    text = re.sub(r"\s+", " ", text)
    return text.strip()
