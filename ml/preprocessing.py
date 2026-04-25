import cv2
import numpy as np
from pathlib import Path
from shared.signal import Signal

FRAME_SAMPLE_RATE = 10        # extract every Nth frame for video
MIN_QUALITY_SCORE = 0.3       # below this, reliability tanks
TARGET_SIZE = (224, 224)      # Xception input size


def preprocess(file_path: str) -> Signal:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".jpg", ".jpeg", ".png"):
        data, quality = _process_image(path)
    elif suffix == ".mp4":
        data, quality = _process_video(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    reliability = _quality_to_reliability(quality)

    return Signal(
        score=quality,
        reliability=reliability,
        module="ml.preprocessing",
        metadata={
            "file": path.name,
            "type": suffix,
            "frames": len(data),
            "quality_score": quality,
        },
    )


def _process_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    frame = _normalise(img)
    quality = _compute_quality(img)
    return [frame], quality


def _process_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {path}")

    frames = []
    qualities = []
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % FRAME_SAMPLE_RATE == 0:
            qualities.append(_compute_quality(frame))
            frames.append(_normalise(frame))
        idx += 1

    cap.release()

    if not frames:
        raise ValueError("No frames extracted from video")

    return frames, float(np.mean(qualities))


def _normalise(frame: np.ndarray) -> np.ndarray:
    resized = cv2.resize(frame, TARGET_SIZE)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0


def _compute_quality(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # normalise to 0–1, cap at 1000 variance as "perfect"
    return float(min(laplacian_var / 1000.0, 1.0))


def _quality_to_reliability(quality: float) -> float:
    if quality < MIN_QUALITY_SCORE:
        return 0.2   # very blurry/corrupt — low trust
    return 0.5 + (quality * 0.5)  # scales 0.3→0.65, 1.0→1.0