import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "connectors"))
sys.path.append(os.path.dirname(__file__))

from generic_single_event_connector import fetch_page_text, extract_event_data
from change_detection import check_for_changes
from update_card import generate_update_card


def recheck_source(source_url, source_name):
    print(f"Rechecking {source_name} ({source_url}) ...")

    html = fetch_page_text(source_url)
    item_data = extract_event_data(html)

    if item_data is None:
        print("  Extraction failed during recheck.")
        return None

    is_new, changes = check_for_changes(source_url, item_data)

    if is_new:
        print("  First time tracking this source's history. No changes to report.")
        return None

    if not changes:
        print("  No changes detected. Staying quiet.")
        return None

    print(f"  {len(changes)} change(s) detected!")
    update_card = generate_update_card(item_data, changes)

    if update_card:
        update_card["source_url"] = source_url
        update_card["source_name"] = source_name
        update_card["changes"] = changes
        print(f"  UPDATE CARD: {update_card['headline']}")
        return update_card

    return None
