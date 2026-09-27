"""Clean OCR text from screenshots and pull out search keywords.

Screenshots of tweets/posts contain interface clutter (handles, timestamps, "1.2K Likes",
"Reply", ...) that ruins searches. clean_ocr() strips it; keywords() picks the words most
likely to identify the story (names first).
"""

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
NOISE = re.compile(rf"""
    https?://\S+ | www\.\S+ | [@#]\w+
  | \b\d{{1,2}}:\d{{2}}\s*(?:am|pm)?\b
  | \b{MONTHS}\s+\d{{1,2}}(?:,?\s*\d{{4}})?\b | \b\d{{1,2}}\s+{MONTHS}(?:\s+\d{{4}})?\b
  | \b\d+(?:[.,]\d+)?\s*[kKmM]?\s+(?:views|likes|reposts|retweets|replies|quotes|bookmarks|comments|shares)\b
  | \b(?:translate\s+post|show\s+more|show\s+this\s+thread|replying\s+to)\b
  | \b\d+\s*[hms]\b
  | [·•|<>{{}}\[\]~_=\\]+
""", re.I | re.X)

# Extra words that carry no meaning for a news search
SEARCH_STOP = ENGLISH_STOP_WORDS | {
    "breaking", "exclusive", "update", "news", "report", "reports", "reported", "says", "said",
    "just", "new", "today", "yesterday", "tonight", "live", "video", "watch", "post", "thread",
}


def clean_ocr(text: str) -> str:
    """Remove interface clutter, then drop leftover lines too short to be real content."""
    lines = []
    for line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", NOISE.sub(" ", line)).strip(" -–—,.:;'\"‘’“”()")
        words = [w for w in line.split() if re.search(r"[A-Za-z]{2,}", w)]
        if len(words) >= 4:
            lines.append(line)
    return "\n".join(lines)


def keywords(text: str, n: int = 6) -> list[str]:
    """Up to n distinctive words, capitalised words (names, places, teams) first."""
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text or "")
    seen, proper, other = set(), [], []
    for i, tok in enumerate(tokens):
        low = tok.lower().strip("'-")
        if low in SEARCH_STOP or low in seen or len(low) < 3:
            continue
        seen.add(low)
        (proper if tok[0].isupper() and not tok.isupper() else other).append(tok.strip("'-"))
    other.sort(key=len, reverse=True)
    return (proper + other)[:n]
