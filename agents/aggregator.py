from shared.signal import Signal

FAKE_THRESHOLD = 0.7
REAL_THRESHOLD = 0.3


def aggregate(
    preprocessing: Signal,
    detection: Signal,
    log_analysis: Signal,
    source: Signal,
) -> dict:
    signals = [preprocessing, detection, log_analysis, source]

    total_reliability = sum(s.reliability for s in signals)

    if total_reliability == 0:
        weights = [1 / len(signals)] * len(signals)
    else:
        weights = [s.reliability / total_reliability for s in signals]

    weight_sum = sum(weights)
    weights = [w / weight_sum for w in weights]

    aggregated_score = sum(
        s.score * w for s, w in zip(signals, weights)
    )

    return {
        "aggregated_score": round(aggregated_score, 4),
        "weight_breakdown": {
            "preprocessing": round(weights[0], 4),
            "detection": round(weights[1], 4),
            "log_analysis": round(weights[2], 4),
            "source": round(weights[3], 4),
        },
        "signal_map": {
            "preprocessing": round(preprocessing.score, 4),
            "detection": round(detection.score, 4),
            "log_analysis": round(log_analysis.score, 4),
            "source": round(source.score, 4),
        },
    }
