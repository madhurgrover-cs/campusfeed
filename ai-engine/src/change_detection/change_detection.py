import json
import os

HISTORY_STORE_PATH = os.path.join("data", "item_history.json")

MONITORED_TOP_LEVEL_FIELDS = ["date_start", "date_end", "item_type"]
MONITORED_DETAIL_KEYS = ["venue", "registration_fee", "prize_pool", "deadline", "eligibility"]


def _load_history():
    if os.path.exists(HISTORY_STORE_PATH):
        with open(HISTORY_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_history(history):
    os.makedirs("data", exist_ok=True)
    temp_path = HISTORY_STORE_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, HISTORY_STORE_PATH)


def _detect_field_changes(old_data, new_data):
    changes = []

    for field in MONITORED_TOP_LEVEL_FIELDS:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        if old_val != new_val and (old_val or new_val):
            changes.append({"field": field, "old_value": old_val, "new_value": new_val})

    old_details = old_data.get("details", {}) or {}
    new_details = new_data.get("details", {}) or {}

    for key in MONITORED_DETAIL_KEYS:
        old_val = old_details.get(key)
        new_val = new_details.get(key)
        if old_val != new_val and (old_val or new_val):
            changes.append({"field": f"details.{key}", "old_value": old_val, "new_value": new_val})

    return changes


def check_for_changes(source_url, new_item_data):
    # Compares new extraction against the last known version of this source.
    # Returns (is_new_source, changes_list). Always saves the new snapshot.
    history = _load_history()

    if source_url not in history:
        history[source_url] = {
            "snapshots": [{"data": new_item_data, "recorded_at": "initial"}]
        }
        _save_history(history)
        return True, []

    previous_snapshot = history[source_url]["snapshots"][-1]["data"]
    changes = _detect_field_changes(previous_snapshot, new_item_data)

    if changes:
        history[source_url]["snapshots"].append({
            "data": new_item_data,
            "recorded_at": f"update_{len(history[source_url]['snapshots'])}",
            "changes_from_previous": changes
        })
        _save_history(history)

    return False, changes
