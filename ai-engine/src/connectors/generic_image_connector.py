import json
import urllib.request
from playwright.sync_api import sync_playwright
from google.genai import types

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from gemini_client import call_gemini_with_retry, strip_json_fence
from cache import already_processed, mark_processed
from schema import CAMPUS_ITEM_SCHEMA_PROMPT


def find_event_images(url, min_width=500, min_height=500, exclude_keywords=None):
    if exclude_keywords is None:
        exclude_keywords = ["logo", "icon", "gradient", "background", "facebook", "x", "linkedin", "instagram", "android", "ios"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(6000)

        images = page.eval_on_selector_all(
            "img",
            "elements => elements.map(el => ({src: el.src, alt: el.alt, width: el.naturalWidth, height: el.naturalHeight}))"
        )
        browser.close()

    event_images = []
    for img in images:
        alt_lower = img["alt"].lower()
        is_excluded = any(k in alt_lower for k in exclude_keywords)
        is_big_enough = img["width"] >= min_width and img["height"] >= min_height
        has_alt_text = len(img["alt"].strip()) > 0

        if is_big_enough and not is_excluded and has_alt_text:
            event_images.append(img)

    return event_images


def extract_event_data(image_bytes, mime_type="image/webp"):
    prompt = "You are an information extraction engine for CampusFeed, SRM's campus intelligence platform. Extract structured data from this poster/notice image.\n\n" + CAMPUS_ITEM_SCHEMA_PROMPT

    response = call_gemini_with_retry([
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt
    ])
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


def run_image_based_connector(source_url, source_name):
    print(f"Fetching event images from {source_name} ({source_url}) ...")
    images = find_event_images(source_url)
    print(f"Found {len(images)} likely event images.")

    cards = []
    for i, img in enumerate(images):
        if already_processed(img["src"]):
            print(f"  Skipping (already processed): {img['alt']}")
            continue

        print(f"--- Processing {i+1}/{len(images)}: {img['alt']} ---")
        try:
            with urllib.request.urlopen(img["src"]) as resp:
                image_bytes = resp.read()

            item_data = extract_event_data(image_bytes)
            if item_data is None:
                print(f"  FAILED: extraction returned nothing (likely rate limit)")
                continue

            card = generate_headline(item_data)
            if card is None:
                print(f"  FAILED: headline generation returned nothing")
                continue

            card["source_url"] = source_url
            card["source_name"] = source_name
            card["image_url"] = img["src"]
            card["connector_type"] = "image_based"
            card["raw_extracted_data"] = item_data
            cards.append(card)

            mark_processed(img["src"], card["headline"])
            print(f"  OK: {card['headline']}")
        except Exception as e:
            print(f"  FAILED on {img['alt']}: {e}")
            continue

    return cards
