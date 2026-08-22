import os
import json
import time
from datetime import date
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

CLIENT = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

FENCE = chr(96) * 3
USAGE_LOG_PATH = os.path.join("data", "usage_log.json")


def strip_json_fence(text):
    cleaned = text.strip()
    if cleaned.startswith(FENCE):
        lines = cleaned.split(chr(10))
        lines = [l for l in lines if not l.strip().startswith(FENCE)]
        cleaned = chr(10).join(lines).strip()
    return cleaned


def log_usage():
    os.makedirs("data", exist_ok=True)
    today = str(date.today())

    log = {}
    if os.path.exists(USAGE_LOG_PATH):
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)

    log[today] = log.get(today, 0) + 1

    with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    return log[today]


def call_gemini_with_retry(contents, max_retries=2, wait_seconds=35):
    for attempt in range(max_retries + 1):
        try:
            response = CLIENT.models.generate_content(model=MODEL, contents=contents)
            calls_today = log_usage()
            print(f"  [Gemini call #{calls_today} today]")
            return response
        except errors.ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries:
                    print(f"  Rate limit hit. Waiting {wait_seconds}s (retry {attempt+1}/{max_retries})...")
                    time.sleep(wait_seconds)
                else:
                    print("  Rate limit hit, retries exhausted. Skipping.")
                    return None
            else:
                raise
    return None
