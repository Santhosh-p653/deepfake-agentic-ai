from shared.signal import Signal

FAKE_THRESHOLD = 0.7
REAL_THRESHOLD = 0.3
MIDDLE_ZONE_LOW = 0.45
MIDDLE_ZONE_HIGH = 0.55
UNIFORM_BOOST = 0.3  # how much to pull weights toward equal


def aggregate(
    preprocessing: Signal,
    detection: Signal,
    log_analysis: Signal,
    source: Signal,
    weight_overrides: dict | None = None,
) -> dict:
    signals = [preprocessing, detection, log_analysis, source]
    names = ["preprocessing", "detection", "log_analysis", "source"]

    if weight_overrides:
        weights = [weight_overrides.get(n, 1.0) for n in names]
    else:
        total_reliability = sum(s.reliability for s in signals)
        if total_reliability == 0:
            weights = [1 / len(signals)] * len(signals)
        else:
            weights = [s.reliability / total_reliability for s in signals]

    weight_sum = sum(weights)
    weights = [w / weight_sum for w in weights]

    aggregated_score = sum(s.score * w for s, w in zip(signals, weights))

    return {
        "aggregated_score": round(aggregated_score, 4),
        "weight_breakdown": {n: round(w, 4) for n, w in zip(names, weights)},
        "signal_map": {n: round(s.score, 4) for n, s in zip(names, signals)},
    }


def compute_path3a_weights(current_breakdown: dict) -> dict:
    """
    Path 3a — uniform boost: pull all weights toward equal by UNIFORM_BOOST.
    Reduces dominance of any single high-reliability module.
    """
    names = list(current_breakdown.keys())
    equal = 1.0 / len(names)
    boosted = {
        n: current_breakdown[n] * (1 - UNIFORM_BOOST) + equal * UNIFORM_BOOST
        for n in names
    }
    total = sum(boosted.values())
    return {n: round(v / total, 4) for n, v in boosted.items()}