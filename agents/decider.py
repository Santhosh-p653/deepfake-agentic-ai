FAKE_THRESHOLD = 0.7
REAL_THRESHOLD = 0.3
MIDDLE_ZONE_LOW = 0.45
MIDDLE_ZONE_HIGH = 0.55

# Hard block — tracks record IDs that have already been reanalysed
_reanalysis_attempted: set[int] = set()


def decide(aggregated: dict, record_id: int) -> dict:
    score = aggregated["aggregated_score"]
    weight_log = aggregated["weight_breakdown"]

    # Hard block — second reanalysis never attempted
    if record_id in _reanalysis_attempted:
        return {
            "verdict": "FLAG_FOR_REVIEW",
            "decision_path": "reanalysis_blocked",
            "weight_log": weight_log,
            "score": score,
            "reanalysis": False,
        }

    if score >= FAKE_THRESHOLD:
        return {
            "verdict": "FAKE",
            "decision_path": f"score {score} >= threshold {FAKE_THRESHOLD}",
            "weight_log": weight_log,
            "score": score,
            "reanalysis": False,
        }

    if score <= REAL_THRESHOLD:
        return {
            "verdict": "REAL",
            "decision_path": f"score {score} <= threshold {REAL_THRESHOLD}",
            "weight_log": weight_log,
            "score": score,
            "reanalysis": False,
        }

    # Middle zone — flag and mark for reanalysis
    _reanalysis_attempted.add(record_id)

    # Path 3a — deep middle zone, trigger uniform weight reanalysis
    if MIDDLE_ZONE_LOW <= score <= MIDDLE_ZONE_HIGH:
        return {
            "verdict": "FLAG_FOR_REVIEW",
            "decision_path": (
                f"score {score} in middle zone "
                f"{MIDDLE_ZONE_LOW}–{MIDDLE_ZONE_HIGH} → Path 3a reanalysis"
            ),
            "weight_log": weight_log,
            "score": score,
            "reanalysis": True,
            "reanalysis_path": "3a",
        }

    # Outer ambiguous zone (0.3–0.45 or 0.55–0.7) — flag, no reanalysis
    return {
        "verdict": "FLAG_FOR_REVIEW",
        "decision_path": (
            f"score {score} in ambiguous range "
            f"{REAL_THRESHOLD}–{FAKE_THRESHOLD}"
        ),
        "weight_log": weight_log,
        "score": score,
        "reanalysis": False,
    }