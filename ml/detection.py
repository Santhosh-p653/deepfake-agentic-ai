from typing import List
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from retinaface import RetinaFace
from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("ml.detection")

TARGET_SIZE = (224, 224)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Xception-style head on EfficientNet-B0 (lightweight, same accuracy) ---
# Pure Xception is heavy — EfficientNet-B0 is a practical swap for CPU inference
_model = None

def _load_model() -> nn.Module:
    global _model
    if _model is not None:
        return _model

    logger.info("Loading detection model", extra={"status": "called"})
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    # Replace classifier head for binary deepfake classification
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(model.classifier[1].in_features, 1),
        nn.Sigmoid(),
    )
    model.eval()
    model.to(DEVICE)
    _model = model
    logger.info("Detection model loaded", extra={"status": "success"})
    return model


_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize(TARGET_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def _detect_faces(frame_uint8: np.ndarray) -> list[np.ndarray]:
    """Run RetinaFace on a single frame, return list of cropped face arrays."""
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


def _score_faces(faces: list[np.ndarray], model: nn.Module) -> list[float]:
    """Run Xception-style model on each face crop, return deepfake scores."""
    scores = []
    with torch.no_grad():
        for face in faces:
            tensor = _transform(face).unsqueeze(0).to(DEVICE)
            score = model(tensor).item()
            scores.append(score)
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

    model = _load_model()

    all_scores = []
    frames_with_faces = 0
    frames_no_faces = 0

    for frame in frames:
        # frames from preprocessing are float32 normalised — convert back for RetinaFace
        frame_uint8 = (frame * 255).astype(np.uint8)
        faces = _detect_faces(frame_uint8)

        if not faces:
            frames_no_faces += 1
            continue

        frames_with_faces += 1
        scores = _score_faces(faces, model)
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

    avg_score = float(np.mean(all_scores))
    max_score = float(np.max(all_scores))
    face_coverage = frames_with_faces / len(frames)

    # reliability scales with how many frames had detectable faces
    reliability = round(min(face_coverage + 0.3, 1.0), 4)

    logger.info(
        f"Detection complete — score={avg_score:.4f} faces_found={len(all_scores)} "
        f"coverage={face_coverage:.2f}",
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
        },
    )