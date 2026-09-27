"""Step 3: look up how reliable a website is, using data/source_ratings.csv."""

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

RATINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "source_ratings.csv"

DOMAIN_IN_TEXT = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|in|co\.uk|int|gov\.in|news)\b", re.I)


@lru_cache(maxsize=1)
def load_ratings() -> dict:
    """Read the CSV once and return {domain: {'rating', 'score', 'aliases'}}."""
    df = pd.read_csv(RATINGS_PATH, keep_default_na=False)
    df["domain"] = df["domain"].str.strip().str.lower()
    return df.set_index("domain")[["rating", "score", "aliases"]].to_dict("index")


@lru_cache(maxsize=1)
def alias_patterns() -> list:
    """[(compiled pattern, domain)] for outlet names and @handles, longest first."""
    pairs = []
    for domain, info in load_ratings().items():
        for alias in filter(None, (a.strip() for a in info["aliases"].split("|"))):
            if alias.startswith("@"):  # handles: exact, case-insensitive, not part of a longer handle
                pat = re.compile(re.escape(alias) + r"(?![A-Za-z0-9_])", re.I)
            else:  # names: case-sensitive so "Mint" doesn't match "mint"
                pat = re.compile(r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])")
            pairs.append((len(alias), pat, domain))
    return [(pat, domain) for _, pat, domain in sorted(pairs, key=lambda p: p[0], reverse=True)]


def check_source(domain: str) -> dict:
    """Return {'domain', 'rating', 'score', 'known'} for a domain.

    score is 0..1 (1 = very reliable). Unknown domains get score None.
    """
    domain = (domain or "").strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]

    info = load_ratings().get(domain)
    if info is None:
        return {"domain": domain, "rating": "unknown", "score": None, "known": False}

    return {
        "domain": domain,
        "rating": info["rating"],
        "score": float(info["score"]),
        "known": True,
    }


def find_source_in_text(text: str):
    """Guess the publisher of a screenshot from website addresses, outlet names or @handles.

    Returns check_source() output plus 'matched' (the text that identified it), or None.
    """
    text = text or ""
    ratings = load_ratings()

    for m in DOMAIN_IN_TEXT.finditer(text):
        parts = m.group(0).lower().split(".")
        for i in range(len(parts) - 1):  # news.bbc.co.uk -> bbc.co.uk
            candidate = ".".join(parts[i:])
            if candidate in ratings:
                return {**check_source(candidate), "matched": m.group(0)}

    for pat, domain in alias_patterns():
        m = pat.search(text)
        if m:
            return {**check_source(domain), "matched": m.group(0)}
    return None
