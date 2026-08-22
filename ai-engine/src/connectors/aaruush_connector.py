"""
CampusFeed Connector: Aaruush Events Page
Fetches live event data from aaruush.org, extracts structured info,
and generates newswire-style headline cards.
"""

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

CLIENT = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

SOURCE_URL = "https://www.aaruush.org/events"
SOURCE_NAME = "Aaruush SRM"

MIN_WIDTH = 500
MIN_HEIGHT = 500
EXCLUDE_ALT_KEYWORDS = ["logo", "icon", "gradient", "background", "facebook", "x", "linkedin", "instagram", "android", "ios"]

FENCE = chr(96) * 3


def strip_json_fence(text):
    cleaned = text.strip()
    if cleaned.startswith(FENCE):
        lines = cleaned.split(chr(10))
        lines = [l for l in lines if not l.strip().startswith(FENCE)]
        cleaned = chr(10).join(lines).strip()
    return cleaned


def find_event_images(url):
    """Render the page with a real browser and return likely event poster images."""
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
        is_excluded = any(k in alt_lower for k in EXCLUDE_ALT_KEYWORDS)
        is_big_enough = img["width"] >= MIN_WIDTH and img["height"] >= MIN_HEIGHT
        has_alt_text = len(img["alt"].strip()) > 0

        if is_big_enough and not is_excluded and has_alt_text:
            event_images.append(img)

    return event_images


def download_image_bytes(url):
    import urllib.request
    with urllib.request.urlopen(url) as response:
        return response.read()


def extract_event_data(image_bytes, mime_type="image/webp"):
    """Send an image to Gemini and get back structured event data."""
    prompt = """
You are an information extraction engine for a campus events platform.
Extract structured data from this event poster image.

Return ONLY valid JSON, no markdown, no explanation, matching exactly this shape:

{
  "title": string,
  "organizer": string,
  "department": string or null,
  "event_type": string,
  "date_start": string or null,
  "date_end": string or null,
  "venue": string or null,
  "team_size": string or null,
  "registration_fee": string or null,
  "prize_pool": string or null,
  "eligibility": string or null,
  "category": string,
  "tags": [string],
  "confidence_notes": string
}

Rules:
- If a field is genuinely ambiguous or not visible, use null and explain in confidence_notes.
- Dates should be normalized (e.g. "2026-08-27") if possible.
- Do not invent information not present in the image.
"""

    response = CLIENT.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt
        ]
    )

    cleaned = strip_json_fence(response.text)
    return json.loads(cleaned)


def generate_headline(event_data):
    """Turn structured event data into an Inshorts-style newswire card."""
    prompt = """
You are the newswire editor for CampusFeed, an Inshorts-style news app for SRM students.
Given structured event data, write a newswire-style card.

Return ONLY valid JSON, no markdown, matching exactly this shape:

{
  "headline": string,
  "one_liner": string,
  "source_tag": string,
  "category_emoji": string
}

Rules:
- headline: under 12 words, punchy, news-style, no clickbait
- one_liner: 1-2 sentences, key facts only, plain and scannable
- source_tag: short attribution
- category_emoji: one relevant emoji
- Do NOT invent facts not present in the data

EVENT DATA:
""" + json.dumps(event_data, indent=2)

    response = CLIENT.models.generate_content(model=MODEL, contents=prompt)
    cleaned = strip_json_fence(response.text)
    return json.loads(cleaned)


def run_connector():
    print(f"Fetching event images from {SOURCE_URL} ...")
    images = find_event_images(SOURCE_URL)
    print(f"Found {len(images)} likely event images.")

    cards = []

    for i, img in enumerate(images):
        print(f"\n--- Processing image {i+1}/{len(images)}: {img['alt']} ---")
        try:
            image_bytes = download_image_bytes(img["src"])
            event_data = extract_event_data(image_bytes)
            card = generate_headline(event_data)
            card["source_url"] = SOURCE_URL
            card["source_name"] = SOURCE_NAME
            card["raw_extracted_data"] = event_data
            cards.append(card)
            print(f"OK: {card['headline']}")
        except Exception as e:
            print(f"FAILED on image {img['alt']}: {e}")
            continue

    return cards


if __name__ == "__main__":
    results = run_connector()

    print("\n" + "=" * 60)
    print(f"NEWSWIRE FEED - {len(results)} cards generated")
    print("=" * 60)

    for card in results:
        print()
        print(f"{card['category_emoji']}  {card['source_tag']}")
        print(card["headline"])
        print(card["one_liner"])

    with open("data/newswire_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved full results to data/newswire_output.json")
