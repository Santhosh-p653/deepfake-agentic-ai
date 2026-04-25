from shared.signal import Signal


def detect(frames: list) -> Signal:
    """
    Stub implementation.
    Returns neutral score with intentionally low reliability.
    Real implementation: RetinaFace + Xception (see GitHub issue).
    """
    return Signal(
        score=0.5,
        reliability=0.1,
        module="ml.detection",
        metadata={
            "stub": True,
            "frames_received": len(frames),
            "note": "static stub — real models not yet implemented",
        },
    )