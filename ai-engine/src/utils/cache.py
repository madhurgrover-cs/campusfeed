import json
import os
import hashlib

CACHE_PATH = os.path.join("data", "processed_items.json")


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs("data", exist_ok=True)
    temp_path = CACHE_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    os.replace(temp_path, CACHE_PATH)


def make_item_id(source_url):
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]


def already_processed(source_url):
    cache = _load_cache()
    return make_item_id(source_url) in cache


def mark_processed(source_url, result_summary):
    cache = _load_cache()
    cache[make_item_id(source_url)] = {
        "source_url": source_url,
        "summary": result_summary
    }
    _save_cache(cache)
