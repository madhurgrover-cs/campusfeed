import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from embeddings import get_embedding, cosine_similarity

CANONICAL_STORE_PATH = os.path.join("data", "canonical_items.json")
SIMILARITY_THRESHOLD = 0.85


def _load_canonical_store():
    if os.path.exists(CANONICAL_STORE_PATH):
        with open(CANONICAL_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_canonical_store(store):
    # Atomic write: write to a temp file, then rename into place.
    # If anything fails mid-write, the original file is never touched.
    os.makedirs("data", exist_ok=True)
    temp_path = CANONICAL_STORE_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, CANONICAL_STORE_PATH)


def _comparison_text(card):
    raw = card.get("raw_extracted_data", {})
    parts = [
        raw.get("title", ""),
        raw.get("organizer", "") or "",
        raw.get("date_start", "") or "",
        card.get("headline", "")
    ]
    return " ".join(p for p in parts if p)


def _quick_filter_match(new_card, existing_canonical):
    new_raw = new_card.get("raw_extracted_data", {})
    existing_raw = existing_canonical["primary_card"].get("raw_extracted_data", {})

    new_date = new_raw.get("date_start")
    existing_date = existing_raw.get("date_start")
    if new_date and existing_date and new_date != existing_date:
        return False

    return True


def find_duplicate(new_card, canonical_store):
    candidates = [c for c in canonical_store if _quick_filter_match(new_card, c)]
    if not candidates:
        return None

    new_embedding = get_embedding(_comparison_text(new_card))
    if new_embedding is None:
        return None

    best_match_idx = None
    best_score = 0

    for canonical in candidates:
        existing_embedding = canonical.get("_embedding")
        if existing_embedding is None:
            continue
        score = cosine_similarity(new_embedding, existing_embedding)
        if score > best_score:
            best_score = score
            best_match_idx = canonical_store.index(canonical)

    if best_score >= SIMILARITY_THRESHOLD:
        print(f"  Duplicate detected (similarity: {best_score:.3f})")
        return best_match_idx

    return None


def add_or_merge_item(new_card, source_type="unknown"):
    canonical_store = _load_canonical_store()

    duplicate_idx = find_duplicate(new_card, canonical_store)

    if duplicate_idx is not None:
        canonical = canonical_store[duplicate_idx]
        canonical["sources"].append({
            "source_url": new_card.get("source_url"),
            "source_name": new_card.get("source_name"),
            "source_type": source_type
        })
        print(f"  Merged into existing canonical item: {canonical['primary_card']['headline']}")
        _save_canonical_store(canonical_store)
        return "merged", duplicate_idx

    new_embedding = get_embedding(_comparison_text(new_card))
    canonical_store.append({
        "primary_card": new_card,
        "sources": [{
            "source_url": new_card.get("source_url"),
            "source_name": new_card.get("source_name"),
            "source_type": source_type
        }],
        "_embedding": new_embedding
    })
    print(f"  Added as new canonical item: {new_card['headline']}")
    _save_canonical_store(canonical_store)
    return "new", len(canonical_store) - 1
