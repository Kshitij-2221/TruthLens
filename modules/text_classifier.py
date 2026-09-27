"""Step 6: predict real vs fake with the model trained in notebooks/train_classifier.ipynb.

The notebook saves a scikit-learn Pipeline (TF-IDF + classifier) to models/fake_news_model.joblib.
Label convention: 1 = real, 0 = fake.
"""

from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "fake_news_model.joblib"


@lru_cache(maxsize=1)
def load_model():
    """Load the saved model once. Returns None if it hasn't been trained yet."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def classify_text(text: str) -> dict:
    """Return {'label', 'score', 'error'} where score = probability the text is real (0..1)."""
    model = load_model()
    if model is None:
        return {"label": None, "score": None, "error": f"No model found at {MODEL_PATH.name}. Train it first."}
    if not text or not text.strip():
        return {"label": None, "score": None, "error": "No text to classify."}

    proba = model.predict_proba([text])[0]
    classes = list(model.classes_)
    real_prob = float(proba[classes.index(1)])

    return {"label": "real" if real_prob >= 0.5 else "fake", "score": real_prob, "error": None}
