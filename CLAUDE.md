# TruthLens

Streamlit app that estimates the credibility of a news article (from a URL) or a screenshot (via OCR).

## Pipeline
1. Input: URL → `modules/url_extractor.py` (requests + BeautifulSoup), or image → `modules/ocr_extractor.py` (Tesseract).
2. `modules/source_checker.py` — looks up the domain in `data/source_ratings.csv` (domain, rating, score 0–1).
3. `modules/claim_checker.py` — Google Fact Check Tools API; key in `.env` as `GOOGLE_FACT_CHECK_API_KEY`.
4. `modules/text_classifier.py` — scikit-learn pipeline loaded from `models/fake_news_model.joblib` (label 1 = real, 0 = fake), trained in `notebooks/train_classifier.ipynb` on Google Colab.
5. `modules/scorer.py` — weighted average of available signals (0–1 each) → score 0–100 + verdict.

## UI
- `app.py` handles flow/state only; all custom HTML lives in `modules/ui.py`, styles in `assets/style.css`, theme in `.streamlit/config.toml`.
- Streamlit 1.64 markup: target `data-testid` selectors (`stTab`, `stTabPanel`, `stTextInputRootElement`, ...), not `data-baseweb`.
- Escape any user/API text with `ui.esc()` before putting it in HTML.

## Conventions
- Every module function returns a dict with an `error` key (None on success) instead of raising, so the UI can show partial results.
- All scores are 0..1 floats, or `None` when a signal is unavailable; the scorer skips `None` and re-weights.
- Never commit `.env` or trained model files.

## Commands
- Install: `pip install -r requirements.txt` (plus Tesseract OCR installed on the system)
- Run: `streamlit run app.py`
