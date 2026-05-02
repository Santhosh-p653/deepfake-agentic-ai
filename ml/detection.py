from typing import Union, List
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("ml.detection")


def detect(frames: Union[int, List]) -> Signal:
    logger.info("Detection invoked", extra={"status": "called"})

    if isinstance(frames, int):
        frames_count = frames
    elif isinstance(frames, list):
        frames_count = len(frames)
    else:
        frames_count = 0

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
            "input_type": type(frames).__name__,
            "note": "static stub — real models not yet implemented",
        },
    )
