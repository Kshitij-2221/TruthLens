"""Step 6: predict real vs fake with the model trained in notebooks/train_classifier.ipynb.

The notebook saves a scikit-learn Pipeline (TF-IDF + classifier) to models/fake_news_model.joblib.
Label convention: 1 = real, 0 = fake.
"""

import re
from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "fake_news_model.joblib"

# Formatting quirks that differ between the dataset's fake and real sources (links, tweets,
# "Getty Images", "Reuters", weekday datelines...). Left in, the model learns these instead of
# the writing itself. KEEP IN SYNC with the copy in notebooks/train_classifier.ipynb.
LEAKS = re.compile(r"""
    https?://\S+ | www\.\S+ | pic\.twitter\.com/\S+ | \S+\.com\b | [@#]\w+
  | \breuters\b | \bgetty\s+images?\b | \bfeatured\s+image\b | \bimage\s+(via|credit)\b
  | \bphoto\s+(by|via|credit)\b | \bvia\s+(twitter|youtube|facebook)\b | \b21st\s+century\s+wire\b
  | \b(video|watch|screenshot|image|images)\b
  | \b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b
""", re.I | re.X)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", LEAKS.sub(" ", str(text))).strip()


@lru_cache(maxsize=1)
def _load_from_disk():
    return joblib.load(MODEL_PATH)


def load_model():
    """Load the saved model once. Returns None if it hasn't been trained yet."""
    if not MODEL_PATH.exists():
        return None  # not cached, so a model added later is picked up
    return _load_from_disk()


def classify_text(text: str) -> dict:
    """Return {'label', 'score', 'error'} where score = probability the text is real (0..1)."""
    model = load_model()
    if model is None:
        return {"label": None, "score": None, "error": f"No model found at {MODEL_PATH.name}. Train it first."}
    if not text or not text.strip():
        return {"label": None, "score": None, "error": "No text to classify."}

    proba = model.predict_proba([clean_text(text)])[0]
    classes = list(model.classes_)
    real_prob = float(proba[classes.index(1)])

    return {"label": "real" if real_prob >= 0.5 else "fake", "score": real_prob, "error": None}
