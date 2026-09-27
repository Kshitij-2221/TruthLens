"""Step 6: predict real vs fake from the writing.

Uses the fine-tuned transformer in models/transformer/ (notebooks/train_transformer.ipynb) when it
exists and torch + transformers are installed; otherwise the TF-IDF pipeline in
models/fake_news_model.joblib (notebooks/train_classifier.ipynb).
Label convention: 1 = real, 0 = fake.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "fake_news_model.joblib"
TRANSFORMER_DIR = MODEL_PATH.parent / "transformer"

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


@lru_cache(maxsize=1)
def _load_transformer():
    """(tokenizer, model, device, max_len, name) or None if unavailable. Loaded once (~1-2 s)."""
    if not (TRANSFORMER_DIR / "config.json").exists():
        return None
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        return None
    meta_path = TRANSFORMER_DIR / "truthlens.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(TRANSFORMER_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(TRANSFORMER_DIR).to(device).eval()
    name = meta.get("base_model", "transformer").split("/")[-1].split("-")[0]
    names = {"distilbert": "DistilBERT", "muril": "MuRIL", "bert": "BERT"}
    return tokenizer, model, device, meta.get("max_len", 256), names.get(name, name)


def _transformer_real_prob(text: str, bundle) -> float:
    import torch

    tokenizer, model, device, max_len, _ = bundle
    enc = tokenizer(text, truncation=True, max_length=max_len, return_tensors="pt").to(device)
    with torch.no_grad():
        probs = torch.softmax(model(**enc).logits.float(), dim=-1)[0]
    return float(probs[model.config.label2id.get("real", 1)])


def classify_text(text: str) -> dict:
    """Return {'label', 'score', 'model', 'error'}; score = probability the text is real (0..1)."""
    if not text or not text.strip():
        return {"label": None, "score": None, "model": None, "error": "No text to classify."}
    cleaned = clean_text(text)

    bundle = _load_transformer()
    if bundle is not None:
        real_prob, model_name = _transformer_real_prob(cleaned, bundle), bundle[4]
    else:
        model = load_model()
        if model is None:
            return {"label": None, "score": None, "model": None,
                    "error": f"No model found at {MODEL_PATH.name}. Train it first."}
        proba = model.predict_proba([cleaned])[0]
        real_prob, model_name = float(proba[list(model.classes_).index(1)]), "TF-IDF"

    return {"label": "real" if real_prob >= 0.5 else "fake", "score": real_prob,
            "model": model_name, "error": None}
