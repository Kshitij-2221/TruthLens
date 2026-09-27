"""Check whether rated news outlets are reporting the same story.

Fact-check databases only cover claims someone has already reviewed, so fresh news usually
has no fact-checks. Coverage by reliable outlets is the next best evidence.

Searches Google News RSS first (fast, no key; its terms allow personal, non-commercial use
only — switch to a paid news API before deploying publicly), then falls back to the GDELT
DOC API (open data, no key, but slow and limited to one request per 5 seconds).
"""

import time
import xml.etree.ElementTree as ET
from functools import lru_cache

import requests

from modules.source_checker import check_source
from modules.text_cleaner import keywords
from modules.url_extractor import get_domain

GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _google_news(query: str, timeout: int) -> list[dict]:
    params = {"q": f"{query} when:30d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    response = requests.get(GOOGLE_NEWS_URL, params=params, timeout=timeout)
    response.raise_for_status()
    articles = []
    for item in ET.fromstring(response.content).iter("item"):
        source = item.find("source")
        outlet = source.text if source is not None else ""
        title = item.findtext("title", "")
        if outlet and title.endswith(" - " + outlet):  # Google appends " - Outlet"
            title = title[: -len(outlet) - 3]
        articles.append({
            "title": title,
            "url": item.findtext("link", ""),
            "domain": get_domain(source.get("url", "")) if source is not None else "",
        })
    return articles


def _gdelt(query: str, timeout: int) -> list[dict]:
    params = {"query": query, "mode": "artlist", "format": "json",
              "maxrecords": 75, "sourcelang": "english", "timespan": "1month"}
    response = requests.get(GDELT_URL, params=params, timeout=timeout)
    if response.status_code == 429 or "limit requests" in response.text[:200]:
        time.sleep(6)
        response = requests.get(GDELT_URL, params=params, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json().get("articles", [])
    except ValueError:  # GDELT reports errors as plain text
        raise requests.RequestException(response.text.strip()[:150])


@lru_cache(maxsize=64)
def _search(query: str, timeout: int) -> list[dict]:
    try:
        return _google_news(query, timeout)  # an empty list is a real answer: nobody reports it
    except (requests.RequestException, ET.ParseError):
        return _gdelt(query, timeout)


def check_coverage(text: str, timeout: int = 12) -> dict:
    """Return {'articles', 'score', 'query', 'error'}.

    articles: relevant reports, each {'title', 'url', 'domain', 'rating', 'score'}.
    score: average reliability (0..1) of the best rated outlets reporting it, or None.
    """
    words = keywords(text, 4)  # names come first; fewer words = better recall
    result = {"articles": [], "score": None, "query": " ".join(words), "error": None}
    if len(words) < 2:
        result["error"] = "Not enough readable text to search the news."
        return result

    try:
        articles = _search(" ".join(words), timeout)
    except requests.RequestException:
        result["error"] = "News search is unavailable right now."
        return result

    # Keep reports whose headline shares at least two of our keywords
    wanted = {w.lower() for w in words}
    seen_urls, relevant = set(), []
    for a in articles:
        title_words = {w.strip(".,:;!?'\"‘’“”()").lower() for w in a.get("title", "").split()}
        if len(wanted & title_words) < min(2, len(wanted)) or a["url"] in seen_urls:
            continue
        seen_urls.add(a["url"])
        src = check_source(a.get("domain", ""))
        relevant.append({"title": a.get("title", ""), "url": a["url"], "domain": src["domain"],
                         "rating": src["rating"], "score": src["score"]})

    # Rated outlets first, most reliable first
    relevant.sort(key=lambda a: -1 if a["score"] is None else a["score"], reverse=True)
    result["articles"] = relevant[:20]

    best_per_domain = {}
    for a in relevant:
        if a["score"] is not None:
            best_per_domain[a["domain"]] = max(a["score"], best_per_domain.get(a["domain"], 0))
    top = sorted(best_per_domain.values(), reverse=True)[:3]
    result["score"] = sum(top) / len(top) if top else None
    return result
