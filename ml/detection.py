from typing import Union, List
from shared.signal import Signal


def detect(frames: Union[int, List]) -> Signal:
    """
    Flexible stub:
    Accepts either:
      - int  → frame count
      - list → actual frames

    This avoids pipeline breakage and keeps compatibility
    for future ML model integration.
    """

    # Determine frame count safely
    if isinstance(frames, int):
        frames_count = frames
    elif isinstance(frames, list):
        frames_count = len(frames)
    else:
        frames_count = 0  # fallback safety

    return Signal(
        score=0.5,
        reliability=0.1,
        module="ml.detection",
        metadata={
            "stub": True,
            "frames_received": frames_count,
            "input_type": type(frames).__name__,
            "note": "static stub — real models not yet implemented",
        },
    )