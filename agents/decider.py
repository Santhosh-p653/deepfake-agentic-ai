from shared.signal import Signal

FAKE_THRESHOLD = 0.7
REAL_THRESHOLD = 0.3

# Hard block — tracks record IDs that have already been reanalysed
_reanalysis_attempted: set[int] = set()


def decide(aggregated: dict, record_id: int) -> dict:
    score = aggregated["aggregated_score"]
    weight_log = aggregated["weight_breakdown"]

    # hard block second reanalysis
    if record_id in _reanalysis_attempted:
        return {
            "verdict": "FLAG_FOR_REVIEW",
            "decision_path": "reanalysis_blocked",
            "weight_log": weight_log,
            "score": score,
        }

    if score >= FAKE_THRESHOLD:
        verdict = "FAKE"
        decision_path = f"score {score} >= threshold {FAKE_THRESHOLD}"
    elif score <= REAL_THRESHOLD:
        verdict = "REAL"
        decision_path = f"score {score} <= threshold {REAL_THRESHOLD}"
    else:
        verdict = "FLAG_FOR_REVIEW"
        decision_path = f"score {score} in ambiguous range {REAL_THRESHOLD}–{FAKE_THRESHOLD}"
        _reanalysis_attempted.add(record_id)

    return {
        "verdict": verdict,
        "decision_path": decision_path,
        "weight_log": weight_log,
        "score": score,
    }
