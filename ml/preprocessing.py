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
        data, quality, extra = _process_image(path)
    elif suffix == ".mp4":
        data, quality, extra = _process_video(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    reliability = _compute_reliability(quality, extra)

    return Signal(
        score=quality,
        reliability=reliability,
        module="ml.preprocessing",
        metadata={
            "file": path.name,
            "type": suffix,
            "frames": len(data),
            "quality_score": quality,
            **extra,
        },
    )


def _process_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    frame = _normalise(img)
    quality = _compute_quality(img)
    extra = {
        "pixel_distribution": _check_pixel_distribution(img),
        "compression_artifact_score": _check_compression_artifacts(img),
        "aspect_ratio_consistent": True,   # single frame, always consistent
    }
    return [frame], quality, extra


def _process_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {path}")

    frames = []
    qualities = []
    pixel_scores = []
    compression_scores = []
    aspect_ratios = set()
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % FRAME_SAMPLE_RATE == 0:
            qualities.append(_compute_quality(frame))
            frames.append(_normalise(frame))
            pixel_scores.append(_check_pixel_distribution(frame))
            compression_scores.append(_check_compression_artifacts(frame))
            h, w = frame.shape[:2]
            aspect_ratios.add((w, h))
        idx += 1

    cap.release()

    if not frames:
        raise ValueError("No frames extracted from video")

    extra = {
        "pixel_distribution": float(np.mean(pixel_scores)),
        "compression_artifact_score": float(np.mean(compression_scores)),
        "aspect_ratio_consistent": len(aspect_ratios) == 1,
    }
    return frames, float(np.mean(qualities)), extra


def _normalise(frame: np.ndarray) -> np.ndarray:
    resized = cv2.resize(frame, TARGET_SIZE)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0


def _compute_quality(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(min(laplacian_var / 1000.0, 1.0))


def _check_pixel_distribution(frame: np.ndarray) -> float:
    """
    Measures how naturally spread pixel values are.
    Synthetically generated or tampered media often has
    unnaturally narrow/clustered pixel distributions.
    Returns 0.0 (suspicious) to 1.0 (natural).
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    non_zero = np.count_nonzero(hist)
    return float(min(non_zero / 200.0, 1.0))   # 200+ active bins = natural


def _check_compression_artifacts(frame: np.ndarray) -> float:
    """
    Estimates compression damage via DCT block artifact detection.
    Heavy compression destroys subtle facial artifacts that
    RetinaFace and Xception rely on.
    Returns 0.0 (heavily compressed) to 1.0 (clean).
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dct = cv2.dct(gray)
    high_freq_energy = np.abs(dct[16:, 16:]).mean()
    total_energy = np.abs(dct).mean() + 1e-6
    ratio = high_freq_energy / total_energy
    return float(min(ratio * 10, 1.0))


def _compute_reliability(quality: float, extra: dict) -> float:
    """
    Aggregates all quality dimensions into a single reliability score.
    Each dimension penalises reliability independently.
    """
    if quality < MIN_QUALITY_SCORE:
        return 0.2

    base = 0.5 + (quality * 0.5)           # 0.65 – 1.0 from sharpness

    # pixel distribution penalty — unnatural clustering
    pixel_score = extra.get("pixel_distribution", 1.0)
    if pixel_score < 0.4:
        base -= 0.15

    # compression penalty — heavy artifacts hurt detection
    compression_score = extra.get("compression_artifact_score", 1.0)
    if compression_score < 0.3:
        base -= 0.15

    # aspect ratio inconsistency — edited/stitched video
    if not extra.get("aspect_ratio_consistent", True):
        base -= 0.2

    return float(max(round(base, 4), 0.0))