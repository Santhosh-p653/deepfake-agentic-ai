import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from ml.detection import detect, _detect_faces, _score_faces
from shared.signal import Signal


def _make_frames(count: int = 3) -> list[np.ndarray]:
    """Generate random normalised float32 frames — same format as preprocessing output."""
    return [np.random.rand(224, 224, 3).astype(np.float32) for _ in range(count)]


def _make_face_crop() -> np.ndarray:
    """Simulate a uint8 face crop."""
    return np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)


# --- Unit: detect() with no frames ---

def test_detect_no_frames_returns_neutral():
    result = detect([])
    assert isinstance(result, Signal)
    assert result.score == 0.5
    assert result.reliability == 0.0
    assert result.module == "ml.detection"
    assert "error" in result.metadata


# --- Unit: detect() with frames but no faces detected ---

def test_detect_no_faces_returns_neutral():
    frames = _make_frames()

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", return_value=[]):

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    assert result.score == 0.5
    assert result.reliability == 0.1
    assert result.metadata["frames_with_faces"] == 0
    assert "no faces detected" in result.metadata["note"]


# --- Unit: detect() with faces — fake scores ---

def test_detect_with_fake_scores():
    frames = _make_frames(3)
    fake_scores = [0.9, 0.85, 0.95]

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", return_value=[_make_face_crop()]), \
         patch("ml.detection._score_faces", return_value=fake_scores):

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    assert result.score == pytest.approx(np.mean(fake_scores * 3), abs=0.01)
    assert result.reliability > 0.1
    assert result.metadata["frames_with_faces"] == 3
    assert result.metadata["faces_scored"] == 9  # 3 frames x 3 scores each


# --- Unit: detect() with real scores ---

def test_detect_with_real_scores():
    frames = _make_frames(2)
    real_scores = [0.1, 0.05]

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", return_value=[_make_face_crop()]), \
         patch("ml.detection._score_faces", return_value=real_scores):

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    assert result.score < 0.3
    assert result.module == "ml.detection"


# --- Unit: score clamped between 0 and 1 ---

def test_detect_score_always_clamped():
    frames = _make_frames(1)

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", return_value=[_make_face_crop()]), \
         patch("ml.detection._score_faces", return_value=[1.5]):  # out of range

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    assert 0.0 <= result.score <= 1.0


# --- Unit: reliability scales with face coverage ---

def test_reliability_scales_with_coverage():
    # 1 of 3 frames has faces — low coverage
    frames = _make_frames(3)
    call_count = {"n": 0}

    def mock_detect_faces(frame):
        call_count["n"] += 1
        return [_make_face_crop()] if call_count["n"] == 1 else []

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", side_effect=mock_detect_faces), \
         patch("ml.detection._score_faces", return_value=[0.8]):

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    # coverage = 1/3, reliability = min(0.33 + 0.3, 1.0) = 0.63
    assert result.reliability == pytest.approx(0.6333, abs=0.01)


# --- Unit: signal contract fields always present ---

def test_detect_signal_has_required_fields():
    frames = _make_frames(2)

    with patch("ml.detection._load_model") as mock_load, \
         patch("ml.detection._detect_faces", return_value=[_make_face_crop()]), \
         patch("ml.detection._score_faces", return_value=[0.7]):

        mock_load.return_value = (MagicMock(), MagicMock())
        result = detect(frames)

    assert hasattr(result, "score")
    assert hasattr(result, "reliability")
    assert hasattr(result, "module")
    assert hasattr(result, "metadata")
    assert "avg_deepfake_score" in result.metadata
    assert "max_deepfake_score" in result.metadata
    assert "face_coverage_ratio" in result.metadata
    assert "model" in result.metadata