
# category_mapper.py

# Mapping of raw keywords to global categories via substring matching
GLOBAL_CATEGORY_MAPPING = {
    "Politics": ["democratic", "election", "party", "government", "minister", "policy", "politics", "congress", "parliament"],
    "Technology": ["ai", "artificial intelligence", "computer", "internet", "software", "chip", "phone", "robot", "digital"],
    "Science": ["space", "nasa", "physics", "biology", "chemistry", "scientist", "science", "experiment", "research"],
    "Health": ["covid", "pandemic", "hospital", "health", "vaccine", "disease", "medical", "doctor"],
    "Business": ["market", "economy", "business", "stock", "investment", "bank", "trade", "finance"],
    "Sports": ["football", "basketball", "tennis", "cricket", "olympics", "sport", "match", "game"],
    "Environment": ["climate", "environment", "pollution", "emission", "conservation", "wildlife", "nature", "green"],
    "Crime": ["murder", "arrest", "police", "criminal", "assault", "violence", "terror", "crime"],
    "World": ["ukraine", "china", "russia", "usa", "war", "conflict", "international", "foreign"],
    "Culture": ["art", "music", "movie", "book", "festival", "cultural", "fashion", "theater"]
}


def map_to_global_categories(raw_categories: list[str]) -> list[str]:
    """Map a list of raw categories to a list of global categories via substring matching."""
    mapped_categories = set()

    for raw in raw_categories:
        lower_raw = raw.lower()
        for global_cat, keywords in GLOBAL_CATEGORY_MAPPING.items():
            if any(keyword in lower_raw for keyword in keywords):
                mapped_categories.add(global_cat)

    return list(mapped_categories) if mapped_categories else ["Other"]
