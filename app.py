"""TruthLens — Streamlit app. Run with:  streamlit run app.py"""

import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

from modules import ui
from modules.claim_checker import check_claim
from modules.coverage_checker import check_coverage
from modules.ocr_extractor import extract_text
from modules.scorer import combine_scores
from modules.source_checker import check_source, find_source_in_text
from modules.text_classifier import classify_text
from modules.text_cleaner import clean_ocr
from modules.url_extractor import extract_article

st.set_page_config(page_title="TruthLens", page_icon="🔍", layout="centered")
ui.inject_css()
ui.hero()


def analyse(text: str, domain: str | None = None, title: str = "") -> dict:
    """domain is None for screenshots: the publisher is then guessed from the text."""
    with st.spinner("Weighing the evidence…"):
        if domain:
            source, clean = check_source(domain), text
        else:
            source, clean = find_source_in_text(text), clean_ocr(text) or text
        facts = check_claim(title or clean)
        coverage = check_coverage(title or clean)
        ml = classify_text(clean)

    # Published fact-checks are the strongest evidence; if there are none (usual for fresh
    # news), fall back to whether reliable outlets are reporting the same story.
    evidence = facts["score"] if facts["score"] is not None else coverage["score"]
    overall = combine_scores(
        source_score=source["score"] if source else None,
        fact_check_score=evidence,
        classifier_score=ml["score"],
    )
    return {"text": text, "clean": clean, "title": title, "domain": domain, "source": source,
            "facts": facts, "coverage": coverage, "ml": ml, "overall": overall}


tab_url, tab_image = st.tabs([":material/link: Article link", ":material/image: Screenshot"])

with tab_url:
    with st.form("url_form", border=False):
        col_input, col_button = st.columns([4, 1], vertical_alignment="bottom")
        url = col_input.text_input(
            "Article link", placeholder="Paste a news article link — https://…",
            label_visibility="collapsed",
        )
        submitted = col_button.form_submit_button("Analyze", type="primary", width="stretch")
    ui.hint("Works with most news sites. If one blocks us, screenshot the article and use the other tab.")

    if submitted:
        if not url.strip():
            st.session_state.result = None
            st.session_state.error = "Paste an article link first."
        else:
            with st.spinner("Fetching the article…"):
                article = extract_article(url.strip())
            if article["error"]:
                st.session_state.result = None
                st.session_state.error = article["error"]
            else:
                st.session_state.error = None
                st.session_state.result = analyse(article["text"], article["domain"], article["title"])

with tab_image:
    upload = st.file_uploader(
        "Drag and drop a screenshot, or click Upload", type=["png", "jpg", "jpeg", "webp"]
    )
    ui.or_divider()
    col_paste, col_hint = st.columns([1, 2], vertical_alignment="center")
    with col_paste:
        pasted = paste_image_button(
            "Paste from clipboard", key="paste_image",
            text_color="#E7EAF2", background_color="#1B2233", hover_background_color="#252E45",
        )
    with col_hint:
        ui.hint("Copy an image first — <kbd>Win</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> "
                "to snip, or right-click an image → Copy image.")

    # Whichever was added most recently wins. The paste button returns its image again on
    # every rerun, so compare pasted images by content to spot a genuinely new paste.
    paste_id = hash(pasted.image_data.tobytes()) if pasted.image_data is not None else None
    if upload is not None and upload.file_id != st.session_state.get("last_upload_id"):
        st.session_state.last_upload_id = upload.file_id
        st.session_state.screenshot = Image.open(upload)
    elif paste_id is not None and paste_id != st.session_state.get("last_paste_id"):
        st.session_state.last_paste_id = paste_id
        st.session_state.screenshot = pasted.image_data
    elif upload is None and paste_id is None:
        st.session_state.pop("screenshot", None)

    image = st.session_state.get("screenshot")
    if image is not None:
        st.image(image, width="stretch")
        if st.button("Analyze screenshot", type="primary", width="stretch"):
            with st.spinner("Reading text from the image…"):
                ocr = extract_text(image)
            if ocr["error"]:
                st.session_state.result = None
                st.session_state.error = ocr["error"]
            else:
                st.session_state.error = None
                st.session_state.result = analyse(ocr["text"])

if st.session_state.get("error"):
    ui.notice(st.session_state.error)

result = st.session_state.get("result")
if result:
    ui.results(result)
    with st.expander("Show the text we analysed"):
        ui.render(f'<div class="tl-fulltext">{ui.esc(result["text"][:5000])}</div>')

ui.footer()
