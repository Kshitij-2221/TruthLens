"""Step 3: look up how reliable a website is, using data/source_ratings.csv."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

RATINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "source_ratings.csv"


@lru_cache(maxsize=1)
def load_ratings() -> dict:
    """Read the CSV once and return {domain: {'rating', 'score'}}."""
    df = pd.read_csv(RATINGS_PATH)
    df["domain"] = df["domain"].str.strip().str.lower()
    return df.set_index("domain")[["rating", "score"]].to_dict("index")


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
