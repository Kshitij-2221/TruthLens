# 🔍 TruthLens

TruthLens helps you judge whether a news article or social-media screenshot is trustworthy. Paste a link or upload an image and it combines three signals into a single credibility score out of 100.

| Signal | How it works |
|---|---|
| **Source reliability** | Looks up the website in a curated list of domain ratings |
| **Fact-check search** | Searches 23k Indian fact-checks offline (Bharat Fake News Kosh) and the Google Fact Check Tools API; if there are none, checks whether reliable outlets are reporting the same story (Google News / GDELT) |
| **Language model** | Fine-tuned DistilBERT transformer (falls back to TF-IDF + Logistic Regression) trained on labelled real/fake news |

## Project structure

```
TruthLens/
├── app.py                  # Streamlit web app
├── assets/style.css        # UI styles
├── .streamlit/config.toml  # Theme
├── requirements.txt
├── modules/
│   ├── url_extractor.py    # Fetch article text from a link
│   ├── source_checker.py   # Website reliability lookup
│   ├── ocr_extractor.py    # Read text from screenshots
│   ├── claim_checker.py    # Fact-check API
│   ├── coverage_checker.py # Who else is reporting the story
│   ├── kosh_search.py      # Offline search of Indian fact-checks
│   ├── text_cleaner.py     # Clean screenshot text, extract keywords
│   ├── text_classifier.py  # ML model prediction
│   ├── scorer.py           # Combine into one score
│   └── ui.py               # HTML components for the interface
├── data/source_ratings.csv # Domain reliability ratings
├── models/                 # Trained model (not committed)
└── notebooks/
    ├── train_classifier.ipynb   # TF-IDF model (fallback)
    └── train_transformer.ipynb  # DistilBERT / MuRIL fine-tuning
```

## Setup

1. **Install Python packages**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
2. **Install Tesseract OCR** (for screenshots) — Windows installer: https://github.com/UB-Mannheim/tesseract/wiki
3. **Add your API key** — create a key for the *Fact Check Tools API* in Google Cloud Console and put it in `.env`:
   ```
   GOOGLE_FACT_CHECK_API_KEY=your_key_here
   ```
4. **Train the transformer** (recommended; needs an NVIDIA GPU or Colab GPU)
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   pip install -r requirements-transformer.txt
   ```
   Run `notebooks/train_transformer.ipynb` with `Fake.csv`/`True.csv` next to it and move the output folder to
   `models/transformer/`. Set `MODEL_NAME = "google/muril-base-cased"` to fine-tune MuRIL instead (only useful with
   Indian-language labelled data). Without it the app uses the TF-IDF model below.

   **TF-IDF fallback model** — open `notebooks/train_classifier.ipynb` in Google Colab, run all cells, download `fake_news_model.joblib` and place it in `models/`.
5. **Build the Indian fact-check index** (optional but recommended) — download
   Bharat Fake News Kosh (search for it on Kaggle), save the `.xlsx` as
   `data/raw/bharatfakenewskosh.xlsx`, then run:
   ```bash
   python -m modules.kosh_search
   ```
   Matching was calibrated on 800 reworded claims vs 1,400 real Indian headlines: a similarity of 0.50 finds 97% of
   reworded claims while falsely matching 0.6% of real news. The dataset's `Label` column is not a real/fake label
   (a text classifier trained on it scores 59.7% vs a 60.7% majority baseline), so it is used for search, not training.
6. **Run**
   ```bash
   streamlit run app.py
   ```

The app still works if the model or API key is missing — it just uses the signals that are available.

## Model comparison

Both models score ~99% on the dataset's own test split, which says little: it comes from the same US 2016–17 sources.
On an out-of-domain check (40 current articles from NDTV, The Hindu, Indian Express, BBC and Hindustan Times, plus 8
hand-written fake-style posts):

| | TF-IDF | DistilBERT |
|---|---|---|
| Real articles judged real | 28/40 | **32/40** |
| Crude fake forwards caught | 3/4 | **4/4** |
| Polished fakes (written like real news) caught | 0/4 | 0/4 |

A style model cannot tell a well-written lie from a well-written truth — that is what the fact-check and news-coverage
signals are for.

## Limitations

- The score is an aid, not a verdict. Always read the linked fact-checks yourself.
- The source list is small; unknown domains are not scored.
- The ML model only learns writing style from its training data and can be fooled.
