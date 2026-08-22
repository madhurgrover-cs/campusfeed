import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)
EMBEDDING_MODEL = "gemini-embedding-001"


def get_embedding(text, max_retries=2, wait_seconds=35):
    for attempt in range(max_retries + 1):
        try:
            result = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
            return result.embeddings[0].values
        except errors.ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries:
                    print(f"  Rate limit hit on embedding. Waiting {wait_seconds}s...")
                    time.sleep(wait_seconds)
                else:
                    print("  Embedding rate limit exhausted, skipping.")
                    return None
            else:
                raise
    return None


def cosine_similarity(vec_a, vec_b):
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = sum(a * a for a in vec_a) ** 0.5
    magnitude_b = sum(b * b for b in vec_b) ** 0.5
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)
