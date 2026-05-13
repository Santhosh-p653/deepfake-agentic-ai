from typing import List
import numpy as np
from PIL import Image
import torch
from transformers import AutoImageProcessor, SiglipForImageClassification
from retinaface import RetinaFace
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("ml.detection")

MODEL_NAME = "prithivMLmods/deepfake-detector-model-v1"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor

    logger.info("Loading deepfake detection model", extra={"status": "called"})
    _processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    _model = SiglipForImageClassification.from_pretrained(MODEL_NAME)
    _model.eval()
    _model.to(DEVICE)
    logger.info("Detection model loaded", extra={"status": "success"})
    return _model, _processor


def _detect_faces(frame_uint8: np.ndarray) -> list[np.ndarray]:
    """Run RetinaFace on a frame, return cropped face arrays."""
    try:
        faces = RetinaFace.detect_faces(frame_uint8)
    except Exception:
        return []

    if not isinstance(faces, dict):
        return []

    crops = []
    h, w = frame_uint8.shape[:2]
    for face in faces.values():
        x1, y1, x2, y2 = face["facial_area"]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame_uint8[y1:y2, x1:x2]
        if crop.size > 0:
            crops.append(crop)

    return crops


def _score_faces(faces: list[np.ndarray], model, processor) -> list[float]:
    """
    Score each face crop.
    Model labels: {"0": "fake", "1": "real"}
    Returns fake probability (label 0) as the deepfake score.
    """
    scores = []
    for face in faces:
        pil_img = Image.fromarray(face).convert("RGB")
        inputs = processor(images=pil_img, return_tensors="pt")
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)
            fake_prob = probs[0][0].item()  # index 0 = "fake"
            fake_prob = max(0.0, min(1.0, fake_prob))  # clamp per-face
            scores.append(fake_prob)

    return scores


def detect(frames: List[np.ndarray]) -> Signal:
    logger.info("Detection invoked", extra={"status": "called"})

    if not frames:
        logger.warning("No frames received", extra={"status": "error"})
        return Signal(
            score=0.5,
            reliability=0.0,
            module="ml.detection",
            metadata={"error": "no frames received"},
        )

    model, processor = _load_model()

    all_scores = []
    frames_with_faces = 0
    frames_no_faces = 0

    for frame in frames:
        frame_uint8 = (frame * 255).astype(np.uint8)
        faces = _detect_faces(frame_uint8)

        if not faces:
            frames_no_faces += 1
            continue

        frames_with_faces += 1
        scores = _score_faces(faces, model, processor)
        all_scores.extend(scores)

    if not all_scores:
        logger.warning(
            "No faces detected in any frame",
            extra={"status": "error"}
        )
        return Signal(
            score=0.5,
            reliability=0.1,
            module="ml.detection",
            metadata={
                "frames_processed": len(frames),
                "frames_with_faces": 0,
                "note": "no faces detected",
            },
        )

    avg_score = max(0.0, min(1.0, float(np.mean(all_scores))))  # clamp
    max_score = max(0.0, min(1.0, float(np.max(all_scores))))   # clamp
    face_coverage = frames_with_faces / len(frames)
    reliability = round(min(face_coverage + 0.3, 1.0), 4)

    logger.info(
        f"Detection complete — score={avg_score:.4f} "
        f"faces={len(all_scores)} coverage={face_coverage:.2f}",
        extra={"status": "success"}
    )

    return Signal(
        score=avg_score,
        reliability=reliability,
        module="ml.detection",
        metadata={
            "frames_processed": len(frames),
            "frames_with_faces": frames_with_faces,
            "frames_no_faces": frames_no_faces,
            "faces_scored": len(all_scores),
            "avg_deepfake_score": avg_score,
            "max_deepfake_score": max_score,
            "face_coverage_ratio": round(face_coverage, 4),
            "model": MODEL_NAME,
        },
    )