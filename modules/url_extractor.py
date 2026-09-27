"""Step 2: fetch an article from a URL and pull out its title and main text."""

import requests
import tldextract
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def get_domain(url: str) -> str:
    """Return the registered domain, e.g. 'https://www.bbc.co.uk/news/x' -> 'bbc.co.uk'."""
    parts = tldextract.extract(url)
    if parts.domain and parts.suffix:
        return f"{parts.domain}.{parts.suffix}".lower()
    return (parts.domain or "").lower()


def extract_article(url: str, timeout: int = 10) -> dict:
    """Download a page and return {'title', 'text', 'domain', 'error'}."""
    result = {"title": "", "text": "", "domain": get_domain(url), "error": None}

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        result["error"] = f"Could not fetch URL: {e}"
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove parts of the page that are not the article
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    # Prefer the <article> tag if the site uses one, otherwise use the whole page
    container = soup.find("article") or soup.body or soup
    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p.split()) > 5]  # skip tiny fragments
    result["text"] = "\n".join(paragraphs)

    if not result["text"]:
        result["error"] = "Page loaded but no article text was found."

    return result
