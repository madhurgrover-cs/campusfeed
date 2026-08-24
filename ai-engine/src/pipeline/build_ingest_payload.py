import os
import sys
import json

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(_SRC, "utils"))
sys.path.append(os.path.join(_SRC, "extraction"))

from cache import make_item_id
from validate import validate_item

SCHEMA_VERSION = "0.1"


def build_ingest_payload(canonical, source_type="unknown"):
    """Compose connector card + dedup canonical + validation into one ingest payload."""
    card = canonical.get("primary_card", {}) or {}
    extracted = card.get("raw_extracted_data", {}) or {}
    source_url = card.get("source_url", "")

    validation = validate_item(extracted, source_type)

    return {
        "item_id": make_item_id(source_url) if source_url else None,
        "schema_version": SCHEMA_VERSION,
        "item_type": extracted.get("item_type"),
        "card": {
            "headline": card.get("headline"),
            "one_liner": card.get("one_liner"),
            "category_emoji": card.get("category_emoji"),
            "source_tag": card.get("source_tag"),
            "image_url": card.get("image_url"),
        },
        "extracted": extracted,
        "sources": canonical.get("sources", []),
        "trust": validation["trust"],
        "sensitivity": validation["sensitivity"],
        "decision": validation["decision"],
        "requires_review": validation["decision"] == "HOLD_FOR_HUMAN_REVIEW",
        "connector_type": card.get("connector_type"),
    }
