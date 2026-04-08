from config import SCORE_HIGH, SCORE_MEDIUM


def fuse(ml_score: float, goplus_flagged: bool, scamdb_match: bool,
         high_threshold: float = SCORE_HIGH) -> dict:
    final_score = ml_score

    if goplus_flagged:
        final_score += 0.15
    if scamdb_match:
        final_score += 0.10

    # If any threat intel source flags it, enforce at least MEDIUM risk.
    # This prevents a low ML score from hiding a known phishing address.
    if goplus_flagged or scamdb_match:
        final_score = max(final_score, SCORE_MEDIUM)

    final_score = round(min(final_score, 1.0), 4)

    if final_score >= high_threshold:
        risk_label = "HIGH"
        risk_color = "red"
    elif final_score >= SCORE_MEDIUM:
        risk_label = "MEDIUM"
        risk_color = "orange"
    else:
        risk_label = "LOW"
        risk_color = "green"

    return {
        "final_score": final_score,
        "risk_label": risk_label,
        "risk_color": risk_color,
    }
