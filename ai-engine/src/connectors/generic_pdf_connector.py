import json
import re
import ssl
import certifi
import urllib.request
from io import BytesIO
from pypdf import PdfReader

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from gemini_client import call_gemini_with_retry, strip_json_fence
from cache import already_processed, mark_processed
from schema import CAMPUS_ITEM_SCHEMA_PROMPT

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def fetch_page_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as response:
        return response.read().decode("utf-8", errors="ignore")


def find_pdf_link(html):
    match = re.search(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_pdf_text(pdf_url):
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as response:
        pdf_bytes = response.read()

    reader = PdfReader(BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages[:5]:
        text_parts.append(page.extract_text() or "")

    return "\n".join(text_parts)


def extract_item_data(text_content):
    prompt = "You are an information extraction engine for CampusFeed, SRM's campus intelligence platform. Extract structured data from this document/brochure content.\n\n" + CAMPUS_ITEM_SCHEMA_PROMPT + "\n\nDOCUMENT TEXT:\n" + text_content[:8000]

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
- one_liner: 1-2 sentences, key facts only
- Do NOT invent facts not present in the data

ITEM DATA:
""" + json.dumps(item_data, indent=2)

    response = call_gemini_with_retry(prompt)
    if response is None:
        return None
    return json.loads(strip_json_fence(response.text))


def run_pdf_connector(page_url, source_name):
    if already_processed(page_url):
        print(f"Already processed: {page_url}")
        return None

    print(f"Fetching page {page_url} ...")
    html = fetch_page_html(page_url)

    pdf_url = find_pdf_link(html)
    if pdf_url is None:
        print("No PDF link found on this page.")
        return None

    if not pdf_url.startswith("http"):
        from urllib.parse import urljoin
        pdf_url = urljoin(page_url, pdf_url)

    print(f"Found PDF: {pdf_url}")
    print("Downloading and extracting PDF text...")

    try:
        pdf_text = extract_pdf_text(pdf_url)
    except Exception as e:
        print(f"Failed to extract PDF: {e}")
        return None

    print(f"Extracted {len(pdf_text)} characters from PDF.")

    if len(pdf_text.strip()) < 50:
        print("PDF text too short/empty - likely a scanned image PDF, not extractable as text.")
        return None

    item_data = extract_item_data(pdf_text)
    if item_data is None:
        print("Extraction failed.")
        return None

    card = generate_headline(item_data)
    if card is None:
        print("Headline generation failed.")
        return None

    card["source_url"] = page_url
    card["source_name"] = source_name
    card["image_url"] = None
    card["connector_type"] = "pdf"
    card["pdf_url"] = pdf_url
    card["raw_extracted_data"] = item_data

    mark_processed(page_url, card["headline"])
    print(f"OK: {card['headline']}")

    return card
