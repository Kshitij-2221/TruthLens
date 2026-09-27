"""Step 7: combine the individual checks into one credibility score (0-100)."""

# How much each signal counts. Missing signals are skipped and the rest re-weighted.
WEIGHTS = {
    "source": 0.30,
    "fact_check": 0.40,
    "classifier": 0.30,
}


def verdict_for(score: float) -> str:
    if score >= 70:
        return "Likely credible"
    if score >= 40:
        return "Uncertain — verify further"
    return "Likely misleading or false"


def combine_scores(source_score=None, fact_check_score=None, classifier_score=None) -> dict:
    """Each input is 0..1 or None. Returns {'score', 'verdict', 'used'}."""
    signals = {
        "source": source_score,
        "fact_check": fact_check_score,
        "classifier": classifier_score,
    }
    used = {name: value for name, value in signals.items() if value is not None}

    if not used:
        return {"score": None, "verdict": "Not enough information", "used": {}}

    total_weight = sum(WEIGHTS[name] for name in used)
    combined = sum(WEIGHTS[name] * value for name, value in used.items()) / total_weight
    score = round(combined * 100, 1)

    return {"score": score, "verdict": verdict_for(score), "used": used}
