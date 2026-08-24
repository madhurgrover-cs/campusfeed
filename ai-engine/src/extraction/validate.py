import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

FENCE = chr(96) * 3


def strip_json_fence(text):
    cleaned = text.strip()
    if cleaned.startswith(FENCE):
        lines = cleaned.split(chr(10))
        lines = [l for l in lines if not l.strip().startswith(FENCE)]
        cleaned = chr(10).join(lines).strip()
    return cleaned


def call_gemini_with_retry(prompt, max_retries=2, wait_seconds=35):
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
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


def score_trust(item_data, source_type):
    """
    Trust scoring based on UNIVERSAL fields that apply to any campus item type,
    not just events. date_start/details are bonus signals, never required -
    a valid safety notice or circular may legitimately have neither.
    """
    score = 0
    reasons = []

    if source_type == "official_website":
        score += 40
        reasons.append("Official institutional source (+40)")
    elif source_type == "student_submission":
        score += 15
        reasons.append("Student submission, unverified source (+15)")
    elif source_type == "news_outlet":
        score += 30
        reasons.append("Third-party news outlet (+30)")
    else:
        reasons.append("Unknown source type (+0)")

    universal_fields = ["title", "organizer", "item_type"]
    filled_universal = sum(1 for f in universal_fields if item_data.get(f))
    universal_score = (filled_universal / len(universal_fields)) * 35
    score += universal_score
    reasons.append(f"{filled_universal}/{len(universal_fields)} core fields present (+{universal_score:.0f})")

    bonus_points = 0
    if item_data.get("date_start"):
        bonus_points += 12
    if item_data.get("details") and len(item_data["details"]) > 0:
        bonus_points += 13
    score += bonus_points
    reasons.append(f"Optional context (date/details) present (+{bonus_points})")

    score = min(100, score)

    if score >= 80:
        label = "Verified"
    elif score >= 55:
        label = "Likely authentic"
    elif score >= 30:
        label = "Needs verification"
    else:
        label = "Conflicting/Unclear"

    return {"trust_score": round(score), "trust_label": label, "trust_reasons": reasons}


def classify_sensitivity(item_data):
    prompt = """
You are a content safety classifier for a campus news app.
Given this campus item data, classify its sensitivity level.

Return ONLY valid JSON matching exactly this shape:

{
  "sensitivity_level": "routine" or "needs_review" or "sensitive",
  "reason": string
}

Classify as "sensitive" if it involves: safety incidents, accidents, violence, protests, 
disciplinary actions, deaths, health emergencies, or anything that could harm someone's 
reputation or cause panic if reported inaccurately.

Classify as "needs_review" if it's ambiguous, involves named individuals in a critical context,
or touches administrative/policy controversy.

Classify as "routine" for normal events, announcements, opportunities, achievements, notices.

DATA:
""" + json.dumps(item_data, indent=2)

    response = call_gemini_with_retry(prompt)
    if response is None:
        return {"sensitivity_level": "needs_review", "reason": "Could not classify - API unavailable, defaulting to safe (human review)"}

    cleaned = strip_json_fence(response.text)
    return json.loads(cleaned)


def validate_item(item_data, source_type):
    trust = score_trust(item_data, source_type)
    sensitivity = classify_sensitivity(item_data)

    if sensitivity["sensitivity_level"] in ("sensitive", "needs_review"):
        decision = "HOLD_FOR_HUMAN_REVIEW"
    elif trust["trust_score"] >= 55:
        decision = "AUTO_PUBLISH"
    else:
        decision = "HOLD_FOR_HUMAN_REVIEW"

    return {"trust": trust, "sensitivity": sensitivity, "decision": decision}
