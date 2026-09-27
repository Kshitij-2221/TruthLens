"""TruthLens — Streamlit app. Run with:  streamlit run app.py"""

import streamlit as st

from modules.claim_checker import check_claim
from modules.ocr_extractor import extract_text
from modules.scorer import combine_scores
from modules.source_checker import check_source
from modules.text_classifier import classify_text
from modules.url_extractor import extract_article

st.set_page_config(page_title="TruthLens", page_icon="🔍", layout="centered")
st.title("🔍 TruthLens")
st.caption("Check how credible a news article or screenshot is.")


def pct(value):
    return "—" if value is None else f"{value * 100:.0f}%"


def show_results(text: str, domain: str | None = None):
    source = check_source(domain) if domain else None
    with st.spinner("Checking fact-check databases..."):
        facts = check_claim(text)
    ml = classify_text(text)

    result = combine_scores(
        source_score=source["score"] if source else None,
        fact_check_score=facts["score"],
        classifier_score=ml["score"],
    )

    st.divider()
    if result["score"] is None:
        st.warning(result["verdict"])
    else:
        st.metric("Credibility score", f"{result['score']} / 100")
        st.progress(result["score"] / 100)
        st.subheader(result["verdict"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Source", pct(source["score"]) if source else "—",
                source["rating"] if source else "n/a")
    col2.metric("Fact-checks", pct(facts["score"]), f"{len(facts['matches'])} found")
    col3.metric("ML model", pct(ml["score"]), ml["label"] or "n/a")

    for err in (facts["error"], ml["error"]):
        if err:
            st.info(err)

    if facts["matches"]:
        st.subheader("Related fact-checks")
        for m in facts["matches"]:
            st.markdown(f"- **{m['rating']}** — {m['claim']}  \n  _{m['publisher']}_ · [read]({m['url']})")

    with st.expander("Text analysed"):
        st.write(text[:5000])


tab_url, tab_image = st.tabs(["🔗 Article link", "🖼️ Screenshot"])

with tab_url:
    url = st.text_input("Paste a news article URL", placeholder="https://...")
    if st.button("Check article", disabled=not url):
        with st.spinner("Fetching article..."):
            article = extract_article(url)
        if article["error"]:
            st.error(article["error"])
        else:
            st.write(f"**{article['title']}**  \n`{article['domain']}`")
            show_results(article["text"], article["domain"])

with tab_image:
    upload = st.file_uploader("Upload a screenshot", type=["png", "jpg", "jpeg", "webp"])
    if upload:
        st.image(upload, use_container_width=True)
        if st.button("Check screenshot"):
            with st.spinner("Reading text from image..."):
                ocr = extract_text(upload)
            if ocr["error"]:
                st.error(ocr["error"])
            else:
                show_results(ocr["text"])
