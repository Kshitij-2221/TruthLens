"""Search 26k Indian fact-checks (Bharat Fake News Kosh) for claims similar to the input.

Google's fact-check API has thin Indian coverage; this local index covers Alt News, BOOM,
India Today, Factly, Vishvas News and more, in 9 languages (searched via English translations).

Build the index once (needs data/raw/bharatfakenewskosh.xlsx):
    python -m modules.kosh_search
"""

import re
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "bharatfakenewskosh.xlsx"
INDEX_PATH = ROOT / "models" / "kosh_index.joblib"

# Calibrated on 800 reworded claims vs 1,400 real Indian headlines (Sep 2026):
#   >= 0.50 finds 97% of reworded claims, falsely matches 0.6% of real headlines -> scored
#   0.40-0.50 is shown as a "similar claim" for context but doesn't affect the score
STRONG_MATCH = 0.50
WEAK_MATCH = 0.40
MIN_QUERY_TERMS = 4  # very short queries give spuriously high similarity

# Fact-check boilerplate that says nothing about *which* claim it is
BOILERPLATE = ENGLISH_STOP_WORDS | {
    "fact", "check", "checked", "checking", "viral", "video", "videos", "image", "images", "photo",
    "photos", "picture", "claim", "claims", "claimed", "claiming", "shared", "sharing", "share",
    "social", "society", "media", "societymedia", "post", "posts", "posted", "users", "user", "read",
    "being", "going", "found", "true", "false", "fake", "misleading", "news", "circulating", "widely",
    "facebook", "twitter", "whatsapp", "netizens", "caption", "truth",
    # outlet names: a headline mentioning "The New York Times" isn't about the same claim
    "times", "york", "hindu", "express", "indian", "ndtv", "bbc", "reuters", "cnn", "today",
    "hindustan", "mint", "print", "wire", "scroll", "tribune", "deccan", "herald", "boom", "alt",
}

DEBUNKED = re.compile(
    r"\b(fake|false|falsely|misleading|mislead|morphed|edited|doctored|manipulated|hoax|rumou?r|"
    r"misattributed|unrelated|not related|old (?:video|image|photo|picture)|passed off|"
    r"shared as|no evidence|baseless|satire|satirical|scripted|clipped|cropped|out of context|"
    r"not from|is not|isn't|did not|didn't|never)\b", re.I)
CONFIRMED = re.compile(r"\b(is true|is correct|is genuine|is real|claim is accurate)\b", re.I)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"http\S+|[@#]\w+", " ", str(text or ""))).strip()


def _verdict(headline: str, body: str):
    """(label, score) guessed from the fact-checker's own wording."""
    text = f"{headline} {body[:400]}"
    if CONFIRMED.search(text) and not DEBUNKED.search(headline):
        return "True", 1.0
    if DEBUNKED.search(text):
        return "False", 0.0
    # No explicit verdict wording (often a question: "Did X happen? Read Fact Check").
    # Being fact-checked at all is strong evidence here: of the verdicts we can detect in
    # this dataset, 96% are "false" — so treat it as disputed rather than ignoring it.
    return "Disputed", 0.25


def build_index(raw_path: Path = RAW_PATH, out_path: Path = INDEX_PATH) -> int:
    import pandas as pd

    df = pd.read_excel(raw_path)
    df = df.drop_duplicates("Fact_Check_Link")
    df["headline"] = df["Eng_Trans_Statement"].fillna(df["Statement"]).map(_clean)
    df["body"] = df["Eng_Trans_News_Body"].fillna(df["News Body"]).map(_clean)
    df = df[df["headline"].str.len() > 15]

    vectorizer = TfidfVectorizer(stop_words=list(BOILERPLATE), ngram_range=(1, 2), min_df=2,
                                 sublinear_tf=True, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
    # Headline counted twice: it names the claim most precisely
    matrix = vectorizer.fit_transform(df["headline"] + " " + df["headline"] + " " + df["body"])

    records = []
    for _, r in df.iterrows():
        label, score = _verdict(r["headline"], r["body"])
        date = pd.to_datetime(r["Publish_Date"], errors="coerce", dayfirst=True)
        records.append({
            "claim": r["headline"], "summary": r["body"][:300], "label": label, "score": score,
            "publisher": r["Fact_Check_Source"], "url": r["Fact_Check_Link"], "language": r["Language"],
            "date": "" if pd.isna(date) else date.strftime("%b %Y"),
        })

    out_path.parent.mkdir(exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "records": records}, out_path, compress=3)
    return len(records)


@lru_cache(maxsize=1)
def _load():
    return joblib.load(INDEX_PATH)


def search(text: str, top_k: int = 5) -> list[dict]:
    """Fact-checks about the same claim, most similar first, in claim_checker's match format.

    Strong matches carry the fact-check's verdict score; weaker "similar claim" matches have
    score None so they're shown but don't move the result. Returns [] if there's no index.
    """
    if not INDEX_PATH.exists() or not (text or "").strip():
        return []
    index = _load()
    query = index["vectorizer"].transform([_clean(text)])
    if query.nnz < MIN_QUERY_TERMS:
        return []
    sims = linear_kernel(query, index["matrix"]).ravel()
    best = sims.argsort()[::-1][:top_k]

    matches = []
    for i in best:
        if sims[i] < WEAK_MATCH:
            break
        r = index["records"][i]
        strong = sims[i] >= STRONG_MATCH
        matches.append({
            "claim": r["claim"],
            "rating": r["summary"] or r["label"],
            "score": r["score"] if strong else None,
            "strong": bool(strong),
            "publisher": f"{r['publisher']} · {r['date']}".strip(" ·"),
            "url": r["url"],
            "similarity": round(float(sims[i]), 2),
        })
    return matches


if __name__ == "__main__":
    n = build_index()
    print(f"Indexed {n} fact-checks -> {INDEX_PATH}")
