import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from gemini_client import call_gemini_with_retry, strip_json_fence


def generate_update_card(item_data, changes):
    change_summary = "; ".join(
        f"{c['field']}: '{c['old_value']}' -> '{c['new_value']}'" for c in changes
    )

    prompt = """You are the newswire editor for CampusFeed, an Inshorts-style news app for SRM students.
An already-known campus item has changed. Write an UPDATE-style newswire card.

Return ONLY valid JSON, no markdown, matching exactly this shape:
{ "headline": string, "change_summary": string, "category_emoji": string }

Rules:
- headline: under 12 words, start with 'UPDATED:' and clearly state what changed
- change_summary: one plain sentence describing old -> new
- Do NOT invent facts not present in the data

ITEM: """ + json.dumps(item_data, indent=2) + """
CHANGES DETECTED: """ + change_summary

    response = call_gemini_with_retry(prompt)
    if response is None:
        return None
    return json.loads(strip_json_fence(response.text))
