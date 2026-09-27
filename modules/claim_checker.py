"""Step 5: search existing fact-checks with the Google Fact Check Tools API.

Needs GOOGLE_FACT_CHECK_API_KEY in .env.
Docs: https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
"""

import os
import re

import requests
from dotenv import load_dotenv

from modules.text_cleaner import clean_ocr, keywords

load_dotenv()

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

# Words commonly used by fact-checkers in their verdicts, mapped to a 0..1 truth score
FALSE_WORDS = ("false", "fake", "hoax", "pants on fire", "incorrect", "fabricated", "misleading", "no evidence")
MIXED_WORDS = ("mixture", "half", "partly", "partially", "mostly false", "exaggerat", "missing context", "unproven")
TRUE_WORDS = ("true", "correct", "accurate", "mostly true")


def rating_to_score(rating: str):
    """Convert a textual verdict like 'Mostly False' to a number, or None if unclear."""
    r = (rating or "").lower()
    if any(w in r for w in MIXED_WORDS):
        return 0.4
    if any(w in r for w in FALSE_WORDS):
        return 0.0
    if any(w in r for w in TRUE_WORDS):
        return 1.0
    return None


def build_queries(text: str, max_queries: int = 3) -> list[str]:
    """Short, clean search queries: the main sentences, then a keyword query."""
    cleaned = clean_ocr(text) or text
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", cleaned) if len(s.split()) >= 5]
    queries = [" ".join(s.split()[:25]) for s in sentences[:max_queries - 1]]
    kw = keywords(cleaned, 6)
    if len(kw) >= 2:
        queries.append(" ".join(kw))
    return queries or [" ".join(text.split()[:25])]


def check_claim(text: str, max_results: int = 5) -> dict:
    """Search fact-checks for the text. Returns {'matches', 'score', 'error'}.

    score is the average truth score (0..1) of matched verdicts, or None if nothing matched.
    """
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        return {"matches": [], "score": None, "error": "GOOGLE_FACT_CHECK_API_KEY is not set in .env"}

    matches, seen = [], set()
    for query in build_queries(text):
        params = {"query": query, "key": api_key, "pageSize": max_results, "languageCode": "en"}
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return {"matches": [], "score": None, "error": f"Fact-check API error: {e}"}

        for claim in data.get("claims", []):
            for review in claim.get("claimReview", []):
                url = review.get("url", "")
                if url in seen:
                    continue
                seen.add(url)
                rating = review.get("textualRating", "")
                matches.append({
                    "claim": claim.get("text", ""),
                    "rating": rating,
                    "score": rating_to_score(rating),
                    "publisher": review.get("publisher", {}).get("name", ""),
                    "url": url,
                })
        if len(matches) >= max_results:
            break
    matches = matches[:max_results]

    scores = [m["score"] for m in matches if m["score"] is not None]
    avg = sum(scores) / len(scores) if scores else None
    return {"matches": matches, "score": avg, "error": None}
