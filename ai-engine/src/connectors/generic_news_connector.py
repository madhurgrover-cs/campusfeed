import json
import os
import urllib.request
import urllib.parse
from dotenv import load_dotenv

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "utils"))
from gemini_client import call_gemini_with_retry, strip_json_fence
from cache import already_processed, mark_processed
from schema import CAMPUS_ITEM_SCHEMA_PROMPT

load_dotenv()

NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY")

RELEVANCE_KEYWORDS = ["srm institute", "srm university", "srmist"]


def is_actually_relevant(article):
    text = (article.get("title", "") + " " + (article.get("description", "") or "")).lower()
    return any(keyword in text for keyword in RELEVANCE_KEYWORDS)


def search_news_mentions(query, max_results=10):
    if not NEWSDATA_API_KEY:
        raise ValueError("NEWSDATA_API_KEY not found. Check your .env file.")

    params = urllib.parse.urlencode({
        "apikey": NEWSDATA_API_KEY,
        "qInTitle": query,
        "language": "en"
    })
    url = f"https://newsdata.io/api/1/news?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    all_results = data.get("results", [])
    relevant = [a for a in all_results if is_actually_relevant(a)]
    print(f"  ({len(all_results)} total results, {len(relevant)} genuinely relevant after filtering)")
    return relevant[:max_results]


def extract_from_article(article):
    title = article.get("title", "")
    description = article.get("description", "") or ""
    pub_date = article.get("pubDate", "")

    combined_text = f"Title: {title}\nPublished: {pub_date}\nDescription: {description}"

    prompt = "You are an information extraction engine for CampusFeed, SRM's campus intelligence platform. Extract structured data from this NEWS ARTICLE excerpt (title + description only, full text not available).\n\n" + CAMPUS_ITEM_SCHEMA_PROMPT + "\n\nARTICLE:\n" + combined_text

    response = call_gemini_with_retry(prompt)
    if response is None:
        return None
    return json.loads(strip_json_fence(response.text))


def generate_headline(item_data):
    prompt = """You are the newswire editor for CampusFeed, an Inshorts-style news app for SRM students.
Given structured campus item data from a NEWS ARTICLE, write a newswire-style card.

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


def run_news_mention_connector(query="SRM University"):
    print(f"Searching news for: {query}")
    articles = search_news_mentions(query)
    print(f"Processing {len(articles)} genuinely relevant articles.")

    cards = []
    for article in articles:
        source_url = article.get("link", "")
        if not source_url or already_processed(source_url):
            print(f"  Skipping (already processed or no URL): {article.get('title', 'untitled')}")
            continue

        print(f"--- Processing: {article.get('title', 'untitled')} ---")
        try:
            item_data = extract_from_article(article)
            if item_data is None:
                continue

            card = generate_headline(item_data)
            if card is None:
                continue

            card["source_url"] = source_url
            card["source_name"] = article.get("source_id", "News mention")
            card["image_url"] = article.get("image_url")
            card["connector_type"] = "news_mention"
            card["source_type"] = "news_outlet"
            card["raw_extracted_data"] = item_data

            mark_processed(source_url, card["headline"])
            cards.append(card)
            print(f"  OK: {card['headline']}")
        except Exception as e:
            print(f"  FAILED: {e}")
            continue

    return cards
