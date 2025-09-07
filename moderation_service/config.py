import os
from typing import List

def _csv_env(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

# === Feature flags ===
TOXICITY_ENABLED = os.getenv("TOXICITY_ENABLED", "true").lower() == "true"
DETOXIFY_MODEL = os.getenv("DETOXIFY_MODEL", "original")

# ALLOW_ALL: if true, moderation will never block articles (useful for testing / guaranteeing delivery)
MODERATION_ALLOW_ALL = os.getenv("MODERATION_ALLOW_ALL", "false").lower() == "true"
# backward-compatibility alias used by code
ALLOW_ALL = MODERATION_ALLOW_ALL

# === Safety / content ===
BANNED_WORDS = _csv_env(
    "BANNED_WORDS",
    default="terrorism,drugs,extremism,hate,genocide"
)

# === Title rules ===
MIN_TITLE_WORDS = int(os.getenv("MIN_TITLE_WORDS", "3"))
MAX_TITLE_WORDS = int(os.getenv("MAX_TITLE_WORDS", "20"))

# === Duplicate detector ===
MAX_DUPLICATE_SENTENCE_RATIO = float(os.getenv("MAX_DUPLICATE_SENTENCE_RATIO", "0.15"))

# === Context validator ===
MIN_KEYWORD_COVERAGE = float(os.getenv("MIN_KEYWORD_COVERAGE", "0.5"))
MAX_KEYWORDS = int(os.getenv("MAX_KEYWORDS", "12"))

# === Misc ===
TORCH_HOME = os.getenv("TORCH_HOME", "/tmp/torch_cache")
os.environ.setdefault("TORCH_HOME", TORCH_HOME)
