from typing import List
import numpy as np
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("ml.detection")


def detect(frames: List[np.ndarray]) -> Signal:
    logger.info("Detection invoked", extra={"status": "called"})

    frames_count = len(frames) if isinstance(frames, list) else 0

    logger.warning(
        f"Detection running as stub — frames={frames_count}",
        extra={"status": "success"}
    )

    return Signal(
        score=0.5,
        reliability=0.1,
        module="ml.detection",
        metadata={
            "stub": True,
            "frames_received": frames_count,
            "note": "static stub — real models not yet implemented",
        },
    )