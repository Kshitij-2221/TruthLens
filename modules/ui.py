"""HTML building blocks for the TruthLens interface. Styles live in assets/style.css."""

import html
from pathlib import Path

import streamlit as st

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style.css"

LOGO = (
    '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="url(#tl-grad)" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<defs><linearGradient id="tl-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">'
    '<stop offset="0" stop-color="#9DB3FF"/><stop offset="1" stop-color="#6EE7D2"/></linearGradient></defs>'
    '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4 21 21"/><path d="m7.9 10.7 1.8 1.8 3.2-3.5"/></svg>'
)

ICONS = {
    "source": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "facts": '<path d="M12 3 20 6v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "model": '<rect x="5" y="5" width="14" height="14" rx="3"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5h.01"/>',
    "arrow": '<path d="M7 17 17 7M9 7h8v8"/>',
}

VERDICTS = {
    "good": ("Likely credible", "Signals point to a trustworthy report.",
             "Still worth a quick look at the original sources."),
    "warn": ("Needs verification", "The evidence is mixed — verify before you share.",
             "Look for the same story from an outlet you already trust."),
    "bad": ("Likely misleading", "Several signals flag this as unreliable.",
            "Treat it with caution and don't share it without checking."),
    "muted": ("Not enough data", "There isn't enough evidence to score this.",
              "Try the full article link instead of a screenshot."),
}

FACT_BADGES = {0.0: ("False", "bad"), 0.25: ("Disputed", "bad"), 0.4: ("Mixed", "warn"), 1.0: ("True", "good")}


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def icon(name: str, cls: str = "") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def tone_for(score) -> str:
    """score is 0..1 (or None)."""
    if score is None:
        return "muted"
    if score >= 0.7:
        return "good"
    if score >= 0.4:
        return "warn"
    return "bad"


def render(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def inject_css():
    render(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>")


def hero():
    render(
        '<div class="tl-hero">'
        f'<div class="tl-logo">{LOGO}</div>'
        '<div class="tl-title">Truth<em>Lens</em></div>'
        '<div class="tl-tag">Check a news link or screenshot against three independent signals — '
        "who published it, what fact-checkers found, and how it's written.</div>"
        '<div class="tl-chips">'
        '<span class="tl-chip"><i style="--c:#8AA4FF"></i>Source reliability</span>'
        '<span class="tl-chip"><i style="--c:#6EE7D2"></i>Fact-check search</span>'
        '<span class="tl-chip"><i style="--c:#C4B5FD"></i>Language model</span>'
        "</div></div>"
    )


def or_divider():
    render('<div class="tl-or">or</div>')


def hint(markup: str):
    render(f'<div class="tl-hint">{markup}</div>')


def notice(message: str, tone: str = "bad"):
    render(f'<div class="tl-notice tone-{tone}">{icon("alert")}<div>{esc(message)}</div></div>')


def footer():
    render(
        '<div class="tl-footer"><b>TruthLens is a guide, not a verdict.</b><br>'
        "The language model learned from 2016–17 US news and can misjudge other regions. "
        "Always read the fact-checks yourself.</div>"
    )


# ---------- Results ----------

def _gauge(score, tone: str) -> str:
    r = 62
    c = 2 * 3.14159 * r
    off = c * (1 - (score or 0) / 100)
    num = f"{score:.0f}" if score is not None else "—"
    return (
        f'<div class="tl-gauge tone-{tone}">'
        f'<svg viewBox="0 0 150 150"><circle class="track" cx="75" cy="75" r="{r}"/>'
        f'<circle class="val" cx="75" cy="75" r="{r}" transform="rotate(-90 75 75)" '
        f'style="--c:{c:.1f};--off:{off:.1f}"/></svg>'
        f'<div class="num"><b>{num}</b><span>OUT OF 100</span></div></div>'
    )


def _signal(kind: str, name: str, weight: int, score, note: str) -> str:
    tone = tone_for(score)
    if score is None:
        value = "Not available"
        bar = ""
    else:
        value = f"{score * 100:.0f}<small>%</small>"
        bar = f'<div class="tl-bar"><i style="--w:{score * 100:.0f}%"></i></div>'
    return (
        f'<div class="tl-card tl-signal tone-{tone}">'
        f'<div class="tl-signal-head"><div class="tl-signal-name">{icon(kind)}{name}</div>'
        f'<div class="tl-weight">{weight}% weight</div></div>'
        f'<div class="tl-signal-val">{value}</div>{bar}'
        f'<div class="tl-signal-note">{esc(note)}</div></div>'
    )


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _source_note(result) -> str:
    source = result["source"]
    if source is None:
        return "Couldn't spot a website, outlet name or @handle in the screenshot."
    found = f"Spotted “{source['matched']}” → " if source.get("matched") else ""
    if not source["known"]:
        return f"{found}{source['domain']} isn't in the ratings list yet."
    return f"{found}{source['domain']} · rated {source['rating']}"


def _evidence(result):
    """(name, score, note) for the evidence signal: fact-checks, else news coverage."""
    facts, coverage = result["facts"], result["coverage"]
    n = len(facts["matches"])
    if facts["score"] is not None:
        scored = sum(m["score"] is not None for m in facts["matches"])
        return "Fact-checks", facts["score"], f"Average verdict across {_plural(scored, 'matching fact-check')}."

    rated = {a["domain"] for a in coverage["articles"] if a["score"] is not None}
    no_fc = "No fact-checks yet" if not facts["error"] else "Fact-check search failed"
    if coverage["score"] is not None:
        names = ", ".join(sorted(rated)[:2]) + ("…" if len(rated) > 2 else "")
        return ("News coverage", coverage["score"],
                f"{no_fc} · reported by {_plural(len(rated), 'rated outlet')} ({names}).")
    if coverage["error"]:
        return "Fact-checks", None, f"{no_fc}, and {coverage['error'][0].lower()}{coverage['error'][1:]}"
    if coverage["articles"]:
        return ("News coverage", None,
                f"{no_fc} · {_plural(len(coverage['articles']), 'report')} found, none from rated outlets.")
    if n:
        return "Fact-checks", None, f"{_plural(n, 'related fact-check')}, but verdicts are unclear."
    return "Fact-checks", None, f"{no_fc}, and no news outlet is reporting this story."


def _model_note(ml) -> str:
    if ml["error"]:
        return ml["error"]
    if ml["label"] == "real":
        return "Writing style reads like professional reporting."
    return "Writing style resembles known fake news."


def _fact_card(m) -> str:
    if m.get("strong") is False:  # local match too loose to trust its verdict
        label, tone = "Similar", "muted"
    else:
        label, tone = FACT_BADGES.get(m["score"], ("Unrated", "muted"))
    rating = m["rating"] if len(m["rating"]) <= 240 else m["rating"][:237] + "…"
    tag = "a" if m["url"] else "div"
    href = f' href="{esc(m["url"])}" target="_blank" rel="noopener noreferrer"' if m["url"] else ""
    return (
        f'<{tag} class="tl-card tl-fact"{href}>'
        f'<div class="tl-badge tone-{tone}">{label}</div><div>'
        f'<div class="tl-fact-claim">{esc(m["claim"])}</div>'
        f'<div class="tl-fact-rating">{esc(rating)}</div>'
        f'<div class="tl-fact-src"><b>{esc(m["publisher"] or "Fact-checker")}</b>'
        f'{icon("arrow") if m["url"] else ""}</div>'
        f"</div></{tag}>"
    )


RATING_BADGES = {"high": ("High", "good"), "mixed": ("Mixed", "warn"),
                 "low": ("Low", "bad"), "satire": ("Satire", "bad")}


def _coverage_card(a) -> str:
    label, tone = RATING_BADGES.get(a["rating"], ("Unrated", "muted"))
    return (
        f'<a class="tl-card tl-fact" href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">'
        f'<div class="tl-badge tone-{tone}">{label}</div><div>'
        f'<div class="tl-fact-claim">{esc(a["title"])}</div>'
        f'<div class="tl-fact-src"><b>{esc(a["domain"])}</b>{icon("arrow")}</div>'
        "</div></a>"
    )


def results(result: dict):
    overall = result["overall"]
    score = overall["score"]
    tone = tone_for(None if score is None else score / 100)
    pill, headline, tip = VERDICTS[tone]
    used = len(overall["used"])

    if result["domain"]:
        avatar = esc(result["domain"][:1].upper())
        title = esc(result["title"] or result["domain"])
        sub = esc(result["domain"])
    else:
        avatar = "Aa"
        words = result["clean"].split()
        title = esc(" ".join(words[:14]) + ("…" if len(words) > 14 else ""))
        via = f" · via {esc(result['source']['domain'])}" if result["source"] else ""
        sub = f"Screenshot · {len(words)} words read{via}"

    summary = (
        '<div class="tl-section"><div class="tl-eyebrow">Verdict</div>'
        f'<div class="tl-card tl-summary tone-{tone}">{_gauge(score, tone)}'
        '<div class="tl-verdict">'
        f'<div class="tl-pill"><i></i>{pill}</div>'
        f'<div class="tl-headline">{headline}</div>'
        f'<div class="tl-explain">Combined from {used} of 3 signals. {tip}</div>'
        f'<div class="tl-meta"><div class="tl-avatar">{avatar}</div>'
        f'<div><div class="tl-meta-title">{title}</div><div class="tl-meta-sub">{sub}</div></div></div>'
        "</div></div></div>"
    )

    source = result["source"]
    ev_name, ev_score, ev_note = _evidence(result)
    signals = (
        '<div class="tl-section"><div class="tl-eyebrow">Signals</div><div class="tl-signals">'
        + _signal("source", "Source", 30, source["score"] if source else None, _source_note(result))
        + _signal("facts", ev_name, 40, ev_score, ev_note)
        + _signal("model", "Language model", 30, result["ml"]["score"], _model_note(result["ml"]))
        + "</div></div>"
    )

    facts = ""
    if result["facts"]["matches"]:
        cards = "".join(_fact_card(m) for m in result["facts"]["matches"][:5])
        facts = ('<div class="tl-section"><div class="tl-eyebrow">What fact-checkers say</div>'
                 f'<div class="tl-facts">{cards}</div></div>')

    coverage = ""
    articles = result["coverage"]["articles"]
    if articles:
        # One report per outlet, rated outlets first (already sorted)
        per_outlet, seen = [], set()
        for a in articles:
            if a["domain"] not in seen:
                seen.add(a["domain"])
                per_outlet.append(a)
        cards = "".join(_coverage_card(a) for a in per_outlet[:5])
        coverage = ('<div class="tl-section"><div class="tl-eyebrow">Who else is reporting this</div>'
                    f'<div class="tl-facts">{cards}</div></div>')

    render(summary + signals + facts + coverage)
