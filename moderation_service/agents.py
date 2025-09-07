import re
import os
import logging
from collections import Counter
from typing import Dict, Any, List

from . import config

logger = logging.getLogger("moderation_agents")
logger.setLevel(os.getenv("MOD_AGENT_LOGLEVEL", "INFO"))

# ------------------------ Utilities ------------------------

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)?")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?\!])\s+")
_SPACE_RE = re.compile(r"\s+")
_QUOTES_RE = re.compile(r"[\"“”‘’]")

_STOPWORDS = set("""
a an and the of in on for to at by from as is are was were be been being it its
this that these those with without into over under after before during about
or nor but so if then than too very more most other another not no yes
he she they we you i me him her them us our your their which who whom whose
""".split())


def normalize_spaces(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").strip())


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def sentence_split(text: str) -> List[str]:
    """
    Conservative sentence splitter.
    Merge extremely tiny fragments (like stray em dashes or bylines) into next sentence,
    but keep normal short sentences distinct. The merge threshold is deliberately low.
    """
    text = normalize_spaces(text)
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    cleaned = []
    buf = ""
    MERGE_IF_SHORTER_THAN = 10  # keep this small so short real sentences are not merged
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) < MERGE_IF_SHORTER_THAN:
            buf = (buf + " " + p).strip()
            continue
        if buf:
            cleaned.append(buf)
            buf = ""
        cleaned.append(p)
    if buf:
        cleaned.append(buf)
    return cleaned


def keyword_candidates(text: str, max_k: int) -> List[str]:
    toks = [t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 2]
    counts = Counter(toks)
    return [w for w, _ in counts.most_common(max_k)]


def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# -------------------- Toxicity backend detection --------------------

_USE_TRANSFORMERS = False
_TRANSFORMER_PIPELINE = None
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch

    device = 0 if torch.cuda.is_available() else -1

    def _init_transformer_pipeline(model_name: str = "unitary/toxic-bert"):
        global _TRANSFORMER_PIPELINE, _USE_TRANSFORMERS
        try:
            tok = AutoTokenizer.from_pretrained(model_name, local_files_only=False)
            mdl = AutoModelForSequenceClassification.from_pretrained(model_name, local_files_only=False)
            _TRANSFORMER_PIPELINE = pipeline("text-classification", model=mdl, tokenizer=tok, device=device, return_all_scores=True)
            _USE_TRANSFORMERS = True
            logger.info(f"[ToxicityAgent] Transformers pipeline initialized with {model_name}")
        except Exception as e:
            logger.warning(f"[ToxicityAgent] Failed to init transformers pipeline ({model_name}): {e}")
            _TRANSFORMER_PIPELINE = None
            _USE_TRANSFORMERS = False

    try:
        _init_transformer_pipeline(os.getenv("TOXIC_MODEL_NAME", "unitary/toxic-bert"))
    except Exception:
        _TRANSFORMER_PIPELINE = None
        _USE_TRANSFORMERS = False

except Exception:
    _USE_TRANSFORMERS = False
    _TRANSFORMER_PIPELINE = None


# ------------------------ Agents ------------------------

class ToxicityAgent:
    """
    ToxicityAgent:
    - Prefer transformers pipeline if available (local heavy model).
    - Otherwise use deterministic keyword/regex fallback.
    Returns normalized shape with common fields.
    """
    def __init__(self):
        self._ready = _USE_TRANSFORMERS and _TRANSFORMER_PIPELINE is not None
        self._pipe = _TRANSFORMER_PIPELINE
        banned_env = os.getenv("BANNED_WORDS", "") or ""
        self._banned_keywords = set(w.strip().lower() for w in banned_env.split(",") if w.strip())
        self._slur_list = {"slur", "fuck", "shit", "nazi", "kkk", "terrorist", "terrorists", "kill", "killing"}
        self._banned_keywords |= self._slur_list

    def run(self, text: str) -> Dict[str, Any]:
        tx = (text or "")
        if not tx.strip():
            return {
                "toxicity": 0.0,
                "severe_toxicity": 0.0,
                "obscene": 0.0,
                "threat": 0.0,
                "insult": 0.0,
                "identity_attack": 0.0,
                "model_loaded": self._ready
            }

        if self._ready and self._pipe:
            try:
                res = self._pipe(tx[:1000])
                scores = {}
                if isinstance(res, list) and len(res) > 0:
                    scores_list = res[0] if isinstance(res[0], list) else res
                    for entry in scores_list:
                        label = str(entry.get("label", "")).lower()
                        score = float(entry.get("score", 0.0))
                        if "tox" in label or "toxic" in label or "toxicity" in label:
                            scores["toxicity"] = max(scores.get("toxicity", 0.0), score)
                        if "severe" in label:
                            scores["severe_toxicity"] = max(scores.get("severe_toxicity", 0.0), score)
                        if "obscene" in label or "sexual" in label:
                            scores["obscene"] = max(scores.get("obscene", 0.0), score)
                        if "threat" in label:
                            scores["threat"] = max(scores.get("threat", 0.0), score)
                        if "insult" in label:
                            scores["insult"] = max(scores.get("insult", 0.0), score)
                        if "identity" in label or "attack" in label:
                            scores["identity_attack"] = max(scores.get("identity_attack", 0.0), score)
                    out = {
                        "toxicity": float(scores.get("toxicity", 0.0)),
                        "severe_toxicity": float(scores.get("severe_toxicity", 0.0)),
                        "obscene": float(scores.get("obscene", 0.0)),
                        "threat": float(scores.get("threat", 0.0)),
                        "insult": float(scores.get("insult", 0.0)),
                        "identity_attack": float(scores.get("identity_attack", 0.0)),
                        "model_loaded": True
                    }
                    return out
            except Exception as e:
                logger.exception(f"[ToxicityAgent] Transformers pipeline failed: {e}")

        # Deterministic fallback
        tl = tx.lower()
        banned_found = [k for k in self._banned_keywords if k in tl]
        toks = tokenize(tx)
        length = max(1, len(toks))
        # crude scoring: proportion of banned words to token count, scaled down for longer articles
        score = min(1.0, len(banned_found) / max(1, length / 8))
        out = {
            "toxicity": float(score),
            "severe_toxicity": 0.0,
            "obscene": float(1.0 if any(w in tl for w in ["fuck", "shit"]) else 0.0),
            "threat": float(1.0 if re.search(r"\bkill\b|\bkilled\b|\bkill(s|ing)?\b", tl) else 0.0),
            "insult": float(1.0 if len(banned_found) > 0 else 0.0),
            "identity_attack": 0.0,
            "model_loaded": False
        }
        return out


class SafeContentAgent:
    """
    Safety heuristics.  IMPORTANT: this agent now *considers* toxicity first.
    If toxicity < threshold => ignore regex hits (to avoid overblocking factual reports like "killed").
    Thresholds are configurable via environment/config.
    """
    def __init__(self):
        self.banned = set([w.lower() for w in config.BANNED_WORDS])
        self.patterns = [
            re.compile(r"\bkill(?:ing|ed|s)?\b", re.I),
            re.compile(r"\b(nazi|kkk|white\s*power)\b", re.I),
            re.compile(r"\bslur\b", re.I),
        ]
        # Threshold under which we relax regex-based blocking
        self.toxicity_threshold = float(getattr(config, "TOXICITY_THRESHOLD", 0.20))

    def run(self, text: str) -> Dict[str, Any]:
        tx = (text or "")
        tl = tx.lower()
        banned_found = sorted({w for w in self.banned if w in tl})

        # Collect regex hits but decision may be relaxed depending on toxicity
        regex_hits = []
        for pat in self.patterns:
            if pat.search(tx):
                regex_hits.append(pat.pattern)

        # Obtain toxicity estimate (use quick lightweight agent to avoid changing main)
        try:
            tox = ToxicityAgent().run(text)
            tox_score = float(tox.get("toxicity", 0.0))
        except Exception:
            tox_score = 0.0

        # If toxicity is below threshold — be permissive (do not mark unsafe due to presence of factual words)
        if tox_score < self.toxicity_threshold:
            safe = True
            effective_regex_hits = []
        else:
            # If toxicity high, respect regex hits and banned words
            safe = (len(banned_found) == 0) and (len(regex_hits) == 0)
            effective_regex_hits = regex_hits

        return {
            "banned_words_found": banned_found,
            "regex_hits": effective_regex_hits,
            "safe": safe,
            "toxicity_score_used": tox_score
        }


class TitleCleanupAgent:
    """
    Clean and choose title candidate.
    """
    def run(self, text: str) -> Dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            return {"original": raw, "candidates": [], "cleaned_title": ""}

        MIN_TITLE_WORDS = getattr(config, "MIN_TITLE_WORDS", 3)
        MAX_TITLE_WORDS = getattr(config, "MAX_TITLE_WORDS", 18)

        RE_WRITTEN_PREFIX = re.compile(
            r'(?im)^(?:revised|rewritten|revision|updated|here(?:\'s)?|note|update|original title|article title|headline|title)\b[^\n\r:]{0,120}[:\-\n\r]?',
            re.IGNORECASE
        )
        DATE_SOURCE_PAREN = re.compile(r'\([^\)]*\b(?:20\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|www\.|http)\b[^\)]*\)')
        URL_RE = re.compile(r'https?://\S+|\bwww\.\S+')
        PARENTHESES = re.compile(r'[\(\[\{].*?[\)\]\}]')
        SEPARATORS = re.compile(r'\n|;|\||\t|—|–| - | \| ')
        DISALLOW_TOKENS = re.compile(r'\b(?:rewrit|revised|original|article|note:|update:|source:|keywords:|related stories|categories:|insert related)\b', re.I)

        s = raw
        lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
        if lines:
            first = lines[0]
            first_candidate = RE_WRITTEN_PREFIX.sub('', first).strip(' .,-–—•:')
            if not re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+\d{1,2},\s*\d{4}', first_candidate) \
               and 'www.' not in first_candidate and 'http' not in first_candidate:
                wc = len(first_candidate.split())
                if MIN_TITLE_WORDS <= wc <= MAX_TITLE_WORDS * 2 and not DISALLOW_TOKENS.search(first_candidate):
                    return {"original": raw, "candidates": [first_candidate], "cleaned_title": re.sub(r'\s+', ' ', first_candidate).strip()}

        s = RE_WRITTEN_PREFIX.sub('', s).strip()
        s = re.sub(r'^\s*(?:[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})(?:\s*[•\-\|]\s*.*)?$', '', s, flags=re.MULTILINE)
        s = DATE_SOURCE_PAREN.sub('', s)
        s = URL_RE.sub('', s)
        s = PARENTHESES.sub(' ', s)
        s = re.sub(r'["“”‘’\']', '', s)
        s = re.sub(r'\s+', ' ', s).strip()

        parts = [p.strip(' .,-–—:•') for p in SEPARATORS.split(s) if p and p.strip()]
        candidates = []
        for p in parts:
            if len(p) < 3:
                continue
            if DISALLOW_TOKENS.search(p):
                continue
            if 'www.' in p or 'http' in p:
                continue
            candidates.append(p)

        if not candidates:
            fallback = s
            if DISALLOW_TOKENS.search(fallback) and ':' in fallback:
                fallback = fallback.split(':')[-1].strip()
            fallback = re.sub(r'^(?:-+|\*+)\s*', '', fallback).strip()
            words = fallback.split()
            if len(words) > MAX_TITLE_WORDS:
                fallback = ' '.join(words[:MAX_TITLE_WORDS])
            cleaned = fallback if fallback and len(fallback) >= 4 else "Untitled"
            return {"original": raw, "candidates": [cleaned], "cleaned_title": cleaned}

        def score_candidate(c: str) -> float:
            toks = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", c)
            wc = len(c.split())
            score = 1.0 - (abs(wc - 10) / 20.0)
            if wc < MIN_TITLE_WORDS:
                score -= 1.0
            if wc > MAX_TITLE_WORDS:
                score -= 0.5 + (wc - MAX_TITLE_WORDS) * 0.05
            if toks:
                sw_ratio = sum(1 for t in toks if t.lower() in _STOPWORDS) / len(toks)
                score -= sw_ratio * 0.25
            if ':' in c:
                score -= 0.2
            score -= (wc - 8) * 0.01
            return score

        best = max(candidates, key=score_candidate)
        words = best.split()
        if len(words) > MAX_TITLE_WORDS:
            best = ' '.join(words[:MAX_TITLE_WORDS])

        return {"original": raw, "candidates": candidates, "cleaned_title": best.strip()}


class QuotedTitleAgent:
    QUOTE_PAT = re.compile(r"[\"“”](.*?)[\"“”]")

    def run(self, text: str) -> Dict[str, Any]:
        raw = (text or "").strip()
        candidates = [m.group(1).strip() for m in self.QUOTE_PAT.finditer(raw)]
        filt = []
        for c in candidates:
            wc = len(c.split())
            if config.MIN_TITLE_WORDS <= wc <= config.MAX_TITLE_WORDS:
                filt.append(c)
        if filt:
            best = max(filt, key=lambda s: min(len(s), 200))
        else:
            best = raw
        return {"original": raw, "candidates": filt or None, "cleaned_title": best.strip()}


class DuplicateCheckerAgent:
    def run(self, text: str) -> Dict[str, Any]:
        sentences = sentence_split(text or "")
        if not sentences:
            return {"total_sentences": 0, "duplicates": 0, "duplicate_ratio": 0.0, "ok": True}

        def norm(s: str) -> str:
            s = s.lower()
            s = re.sub(r"[\W_]+", " ", s)
            s = normalize_spaces(s)
            return s

        seen = set()
        dup_count = 0
        for s in sentences:
            key = norm(s)
            if key in seen:
                dup_count += 1
            else:
                seen.add(key)

        ratio = dup_count / max(1, len(sentences))
        logger.debug(f"[DuplicateChecker] total_sentences={len(sentences)} duplicates={dup_count} ratio={ratio:.3f}")

        return {
            "total_sentences": len(sentences),
            "duplicates": dup_count,
            "duplicate_ratio": ratio,
            "ok": ratio <= getattr(config, "MAX_DUPLICATE_SENTENCE_RATIO", 0.30)
        }


# -------------------- Context validator with optional embeddings --------------------

_USE_EMBEDDINGS = False
_EMBED_MODEL = None
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    def _init_embedding_model():
        global _EMBED_MODEL, _USE_EMBEDDINGS
        try:
            model_name = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
            _EMBED_MODEL = SentenceTransformer(model_name)
            _USE_EMBEDDINGS = True
            logger.info(f"[ContextValidator] Loaded embedding model {model_name}")
        except Exception as e:
            _EMBED_MODEL = None
            _USE_EMBEDDINGS = False
            logger.warning(f"[ContextValidator] Failed to load SentenceTransformer: {e}")

    try:
        _init_embedding_model()
    except Exception:
        _EMBED_MODEL = None
        _USE_EMBEDDINGS = False

except Exception:
    _USE_EMBEDDINGS = False
    _EMBED_MODEL = None


class ContextValidatorAgent:
    """
    Ensures rewritten text preserves key context from the original.
    Combines keyword coverage with optional embedding similarity.
    """
    def __init__(self):
        self.max_keywords = getattr(config, "MAX_KEYWORDS", 12)
        self.min_coverage = float(getattr(config, "MIN_KEYWORD_COVERAGE", 0.45))

    def _cosine(self, a, b) -> float:
        try:
            import numpy as np
            a = np.array(a); b = np.array(b)
            denom = (np.linalg.norm(a) * np.linalg.norm(b))
            if denom == 0:
                return 0.0
            return float(np.dot(a, b) / denom)
        except Exception:
            return 0.0

    def run(self, original_text: str, rewritten_text: str) -> Dict[str, Any]:
        orig = original_text or ""
        rw = rewritten_text or ""
        if not orig or not rw:
            return {"keywords": [], "present": [], "coverage": 0.0, "ok": True, "embedding_similarity": None}

        keys = keyword_candidates(orig, self.max_keywords)
        present = [k for k in keys if re.search(rf"\b{re.escape(k)}\b", rw, flags=re.I)]
        coverage = (len(present) / max(1, len(keys))) if keys else 1.0

        embedding_similarity = None
        ok = coverage >= self.min_coverage

        if _USE_EMBEDDINGS and _EMBED_MODEL:
            try:
                v1 = _EMBED_MODEL.encode(orig, convert_to_numpy=True)
                v2 = _EMBED_MODEL.encode(rw, convert_to_numpy=True)
                sim = float(self._cosine(v1, v2))
                embedding_similarity = sim
                threshold = float(os.getenv("EMBED_SIM_THRESHOLD", "0.62"))
                ok = ok and (sim >= threshold)
            except Exception as e:
                logger.exception(f"[ContextValidator] Embedding similarity failed: {e}")

        return {
            "keywords": keys,
            "present": present,
            "coverage": coverage,
            "ok": ok,
            "embedding_similarity": embedding_similarity
        }
