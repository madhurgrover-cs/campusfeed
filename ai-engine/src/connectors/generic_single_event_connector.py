import re
import json
import urllib.request

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from gemini_client import call_gemini_with_retry, strip_json_fence
from cache import already_processed, mark_processed
from schema import CAMPUS_ITEM_SCHEMA_PROMPT


def fetch_page_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode("utf-8", errors="ignore")
    return html


def extract_og_image(html):
    match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)
    return None


def extract_event_data(page_text):
    prompt = "You are an information extraction engine for CampusFeed, SRM's campus intelligence platform. Extract structured data about the SINGLE campus item described in this web page (ignore navigation menus, footers, unrelated content).\n\n" + CAMPUS_ITEM_SCHEMA_PROMPT + "\n\nPAGE TEXT:\n" + page_text[:8000]

    response = call_gemini_with_retry(prompt)
    if response is None:
        return None
    return json.loads(strip_json_fence(response.text))


def generate_headline(item_data):
    prompt = """You are the newswire editor for CampusFeed, an Inshorts-style news app for SRM students.
Given structured campus item data, write a newswire-style card.

Return ONLY valid JSON, no markdown, matching exactly this shape:
{ "headline": string, "one_liner": string, "source_tag": string, "category_emoji": string }

Rules:
- headline: under 12 words, punchy, news-style
- one_liner: 1-2 sentences, key facts only - include notable_attendees and important details if present
- Do NOT invent facts not present in the data

ITEM DATA:
""" + json.dumps(item_data, indent=2)

    response = call_gemini_with_retry(prompt)
    if response is None:
        return None
    return json.loads(strip_json_fence(response.text))


def run_single_event_connector(source_url, source_name):
    if already_processed(source_url):
        print(f"Already processed: {source_url}")
        return None

    print(f"Fetching {source_name} ({source_url}) ...")
    html = fetch_page_text(source_url)
    print(f"Fetched {len(html)} characters.")

    image_url = extract_og_image(html)
    print(f"Image found: {image_url if image_url else 'none'}")

    item_data = extract_event_data(html)
    if item_data is None:
        print("Extraction failed.")
        return None

    card = generate_headline(item_data)
    if card is None:
        print("Headline generation failed.")
        return None

    card["source_url"] = source_url
    card["source_name"] = source_name
    card["image_url"] = image_url
    card["connector_type"] = "static_html"
    card["raw_extracted_data"] = item_data

    mark_processed(source_url, card["headline"])
    print(f"OK: {card['headline']}")

    return card
