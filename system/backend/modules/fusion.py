from config import SCORE_HIGH, SCORE_MEDIUM


def fuse(ml_score: float, goplus_flagged: bool, scamsniffer_flagged: bool,
         high_threshold: float = SCORE_HIGH) -> dict:
    final_score = ml_score

    if goplus_flagged:
        final_score += 0.15
    if scamsniffer_flagged:
        final_score += 0.10

    # If any threat intel source flags it, enforce at least MEDIUM risk.
    # This prevents a low ML score from hiding a known phishing address.
    if goplus_flagged or scamsniffer_flagged:
        final_score = max(final_score, SCORE_MEDIUM)

    final_score = round(min(final_score, 1.0), 4)

    if final_score >= high_threshold:
        risk_label = "HIGH"
    elif final_score >= SCORE_MEDIUM:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    return {
        "final_score": final_score,
        "risk_label": risk_label,
    }
