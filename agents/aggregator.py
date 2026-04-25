from shared.signal import Signal

# Thresholds — tune after real model experimentation
FAKE_THRESHOLD = 0.7
REAL_THRESHOLD = 0.3


def aggregate(
    preprocessing: Signal,
    detection: Signal,
    log_analysis: Signal,
) -> dict:
    signals = [preprocessing, detection, log_analysis]

    # compute raw weights from reliability
    total_reliability = sum(s.reliability for s in signals)

    if total_reliability == 0:
        weights = [1 / len(signals)] * len(signals)
    else:
        weights = [s.reliability / total_reliability for s in signals]

    # normalise weights so they sum to 1
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
        },
        "signal_map": {
            "preprocessing": round(preprocessing.score, 4),
            "detection": round(detection.score, 4),
            "log_analysis": round(log_analysis.score, 4),
        },
  }
