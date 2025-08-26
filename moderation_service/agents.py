from detoxify import Detoxify
import re

# Initialize model once
toxicity_model = Detoxify('original')

class ToxicityAgent:
    def run(self, text: str) -> dict:
        """Check toxicity levels"""
        raw = toxicity_model.predict(text)
        return {k: float(v) for k, v in raw.items()}

class SafeContentAgent:
    def run(self, text: str) -> dict:
        """Simple keyword filter"""
        banned = ["terrorism", "drugs"]
        found = [word for word in banned if word in text.lower()]
        return {"banned_words_found": found, "safe": len(found) == 0}

class TitleCleanupAgent:
    def run(self, text: str) -> dict:
        """Fallback cleanup for rewritten titles"""
        cleaned = re.sub(r'(?i)rewritten\s*title:?', '', text)
        cleaned = re.sub(r'(?i)rewritten:', '', cleaned)
        cleaned = cleaned.replace('"', ' ').replace("'", " ")
        cleaned = re.sub(r'\s+', ' ', cleaned)

        candidates = re.split(r';|\n| in ', cleaned)
        processed = []
        for c in candidates:
            c = c.strip()
            if len(c.split()) < 3: 
                continue
            if "rewritten" in c.lower():
                continue
            processed.append(c)

        if processed:
            best = max(processed, key=lambda x: len(x.split()))
            if len(best.split()) > 20:
                best = " ".join(best.split()[:20])
        else:
            best = cleaned.strip()

        return {
            "original": text.strip(),
            "candidates": processed,
            "cleaned_title": best.strip()
        }

class QuotedTitleAgent:
    def run(self, text: str) -> dict:
        """
        Extracts titles only inside quotes ("...") or ('...').
        Falls back to raw text if nothing valid found.
        """
        candidates = re.findall(r'["“”](.*?)["“”]', text) + re.findall(r"[‘’](.*?)[‘’]", text)
        processed = []

        for c in candidates:
            c = c.strip()
            if 3 <= len(c.split()) <= 20:  # reasonable length
                processed.append(c)

        if processed:
            best = max(processed, key=lambda x: len(x.split()))
        else:
            best = text.strip()

        return {
            "original": text.strip(),
            "candidates": processed,
            "cleaned_title": best.strip()
        }

def moderate_text(text: str) -> dict:
    """Combine all agents here"""
    return {
        "toxicity": ToxicityAgent().run(text),
        "safety": SafeContentAgent().run(text),
        "title_cleanup": TitleCleanupAgent().run(text),
        "quoted_title": QuotedTitleAgent().run(text)
    }
