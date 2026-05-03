import cv2
import hashlib
import numpy as np
from pathlib import Path
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("ml.preprocessing")

FRAME_SAMPLE_RATE = 10
MIN_QUALITY_SCORE = 0.3
TARGET_SIZE = (224, 224)
DCT_CAP = 256  # max frame dimension for DCT to keep video processing fast

UPLOADS_ROOT = Path("/app/uploads").resolve()
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".mp4"}


def _safe_resolve(file_path: str) -> Path:
    try:
        resolved = Path(file_path).resolve()
    except (TypeError, ValueError):
        raise ValueError("Invalid file path.")

    # Fix #5: use is_relative_to() instead of startswith() to prevent
    # path prefix collisions e.g. /app/uploads_evil/file.jpg
    if not resolved.is_relative_to(UPLOADS_ROOT):
        raise ValueError("File not found.")

    if not resolved.is_file():
        raise ValueError("File not found.")

    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported file type.")

    return resolved


def _extract_source_metadata(path: Path) -> dict:
    # Fix #1: guard here so CodeQL sees a boundary check at the taint sink,
    # even if this function is called independently of _safe_resolve
    if not path.resolve().is_relative_to(UPLOADS_ROOT):
        raise ValueError("File not found.")

    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)
    suffix = path.suffix.lower()

    has_metadata = False
    exif_fields_found = []

    if suffix in (".jpg", ".jpeg"):
        try:
            import piexif
            # piexif.load() accepts raw bytes directly — this is intentional
            exif_data = piexif.load(file_bytes)
            has_metadata = any(
                exif_data.get(ifd) for ifd in ("0th", "Exif", "GPS", "1st")
            )
            if has_metadata:
                exif_fields_found = list(exif_data.get("0th", {}).keys())
        except Exception:
            has_metadata = False

    elif suffix == ".png":
        has_metadata = b"tEXt" in file_bytes or b"iTXt" in file_bytes

    elif suffix == ".mp4":
        has_metadata = b"moov" in file_bytes and b"udta" in file_bytes

    return {
        "file_hash": file_hash,
        "file_size_bytes": file_size,
        "has_metadata": has_metadata,
        "exif_fields_found": exif_fields_found,
        "extension": suffix,
    }


def preprocess(file_path: str) -> tuple[list[np.ndarray], Signal]:
    """
    Returns (frames, Signal).
    frames — list of normalised numpy arrays, never serialized.
    Signal — JSON-safe, sent over HTTP to agents.
    """
    logger.info(
        f"Preprocessing invoked — file={Path(file_path).name}",
        extra={"status": "called"}
    )

    try:
        path = _safe_resolve(file_path)
    except ValueError as e:
        logger.error(f"Path validation failed — {e}", extra={"status": "error"})
        raise

    suffix = path.suffix.lower()

    logger.info("Source metadata extraction invoked", extra={"status": "called"})
    source_meta = _extract_source_metadata(path)
    logger.info("Source metadata extraction complete", extra={"status": "success"})

    try:
        if suffix in (".jpg", ".jpeg", ".png"):
            frames, quality, extra = _process_image(path)
        elif suffix == ".mp4":
            frames, quality, extra = _process_video(path)
        else:
            raise ValueError("Unsupported file type.")
    except ValueError as e:
        logger.error(f"Preprocessing failed — {e}", extra={"status": "error"})
        raise

    reliability = _compute_reliability(quality, extra)

    logger.info(
        f"Preprocessing complete — frames={len(frames)} "
        f"quality={round(quality, 4)} reliability={reliability}",
        extra={"status": "success"}
    )

    signal = Signal(
        score=quality,
        reliability=reliability,
        module="ml.preprocessing",
        metadata={
            "file": path.name,
            "type": suffix,
            "frame_count": len(frames),  # count only — arrays never serialized
            "quality_score": quality,
            "source": source_meta,
            **extra,
        },
    )

    return frames, signal


def _process_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError("Could not read file.")
    frame = _normalise(img)
    quality = _compute_quality(img)
    extra = {
        "pixel_distribution": _check_pixel_distribution(img),
        "compression_artifact_score": _check_compression_artifacts(img),
        "aspect_ratio_consistent": True,
    }
    return [frame], quality, extra


def _process_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not read file.")

    frames, qualities, pixel_scores, compression_scores = [], [], [], []
    aspect_ratios = set()
    idx = 0

    # Fix #3: guarantee cap.release() even if an exception is raised mid-loop
    try:
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
    finally:
        cap.release()

    if not frames:
        raise ValueError("No frames could be extracted.")

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

    # Fix #4: log blank/uniform frames so they don't silently degrade reliability
    if laplacian_var == 0.0:
        logger.warning(
            "Zero Laplacian variance — blank or uniform frame detected",
            extra={"status": "warning"}
        )

    return float(min(laplacian_var / 1000.0, 1.0))


def _check_pixel_distribution(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    non_zero = np.count_nonzero(hist)
    return float(min(non_zero / 200.0, 1.0))


def _check_compression_artifacts(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    new_h = h if h % 2 == 0 else h - 1
    new_w = w if w % 2 == 0 else w - 1
    gray = gray[:new_h, :new_w]

    # Fix #6: cap DCT input dimensions to DCT_CAP x DCT_CAP to keep
    # per-frame processing fast for video without losing artifact signal
    gray = gray[:min(new_h, DCT_CAP), :min(new_w, DCT_CAP)]

    dct = cv2.dct(gray)
    high_freq_energy = np.abs(dct[16:, 16:]).mean()
    total_energy = np.abs(dct).mean() + 1e-6
    ratio = high_freq_energy / total_energy
    return float(min(ratio * 10, 1.0))


def _compute_reliability(quality: float, extra: dict) -> float:
    if quality < MIN_QUALITY_SCORE:
        return 0.2

    base = 0.5 + (quality * 0.5)

    if extra.get("pixel_distribution", 1.0) < 0.4:
        base -= 0.15

    if extra.get("compression_artifact_score", 1.0) < 0.3:
        base -= 0.15

    if not extra.get("aspect_ratio_consistent", True):
        base -= 0.2

    return float(max(round(base, 4), 0.0))
    
