import os
import sys
import json

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_ROOT, "src", "connectors"))
sys.path.append(os.path.join(_ROOT, "src", "dedup"))
sys.path.append(os.path.join(_ROOT, "src", "pipeline"))

from generic_single_event_connector import run_single_event_connector
from dedup import add_or_merge_item, _load_canonical_store
from build_ingest_payload import build_ingest_payload

SOURCE_TYPE = "official_website"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python run_pipeline_test.py <url> [source_name]")
        sys.exit(1)

    url = sys.argv[1]
    source_name = sys.argv[2] if len(sys.argv) > 2 else "SRM official website"

    card = run_single_event_connector(url, source_name)
    if card is None:
        print("No card produced (already processed, or extraction failed).")
        sys.exit(0)

    card["source_type"] = SOURCE_TYPE

    status, idx = add_or_merge_item(card, source_type=SOURCE_TYPE)
    canonical = _load_canonical_store()[idx]
    payload = build_ingest_payload(canonical, source_type=SOURCE_TYPE)

    print(f"{status}: type={payload['item_type']} trust={payload['trust']['trust_score']} review={payload['requires_review']}")

    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", "ingest_payloads.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([payload], f, indent=2, ensure_ascii=False)
    print(f"Wrote payload to {out_path}")
