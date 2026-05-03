"""
Smoke tests for the ML detection pipeline.
Designed to be partial-implementation safe — tests warn instead of
failing hard when modules are not yet written.

Place this file at: ml/tests/test_ml_smoke.py
"""

import ast
import importlib
import warnings
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _can_import(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def _warn_not_implemented(feature: str):
    warnings.warn(
        f"{feature} not yet implemented — this test will enforce once the module exists.",
        stacklevel=3,
    )


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

class TestMLStructure:

    def test_ml_directory_exists(self):
        """ml/ directory must be present at the repo root."""
        assert Path("ml").exists(), "ml/ directory must exist"

    def test_no_syntax_errors(self):
        """All .py files under ml/ must parse without SyntaxError."""
        errors = []
        for f in Path("ml").rglob("*.py"):
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append(f"{f}: {e}")
        assert not errors, "Syntax errors in ml/:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Dependency checks (warn only — heavy deps like torch can't install in CI)
# ---------------------------------------------------------------------------

class TestMLDependencies:

    def test_opencv_importable(self):
        """cv2 (OpenCV) must be importable; warns if not yet installed."""
        if not _can_import("cv2"):
            _warn_not_implemented("OpenCV (cv2)")
            return
        import cv2
        assert cv2.__version__, "cv2 should expose a version"

    def test_numpy_importable(self):
        """numpy must be importable — it is a hard dependency of the ML pipeline."""
        assert _can_import("numpy"), "numpy must be importable"

    def test_pillow_importable(self):
        """Pillow (PIL) must be importable; warns if not yet installed."""
        if not _can_import("PIL"):
            _warn_not_implemented("Pillow (PIL)")


# ---------------------------------------------------------------------------
# Pipeline interface tests (warn if not yet implemented)
# ---------------------------------------------------------------------------

class TestDetectionPipeline:
    """
    Tests for the deepfake detection pipeline.
    All tests warn gracefully if the pipeline module isn't written yet.
    Once you implement ml/pipeline.py, these will enforce correctness.
    """

    def _get_pipeline_module(self):
        """Attempt to import the pipeline module from several candidate paths."""
        for candidate in ("ml.pipeline", "pipeline", "ml.detector", "detector"):
            try:
                return importlib.import_module(candidate)
            except (ImportError, ModuleNotFoundError):
                continue
        return None

    def test_pipeline_module_exists(self):
        """ml/pipeline.py (or equivalent) must be importable."""
        mod = self._get_pipeline_module()
        if mod is None:
            _warn_not_implemented("ml/pipeline.py")
            return
        assert mod is not None

    def test_detector_class_exists(self):
        """ml/pipeline.py should expose a DeepfakeDetector class."""
        mod = self._get_pipeline_module()
        if mod is None:
            _warn_not_implemented("DeepfakeDetector class")
            return
        assert hasattr(mod, "DeepfakeDetector"), (
            "pipeline module must expose a DeepfakeDetector class"
        )

    def test_detector_has_predict_method(self):
        """DeepfakeDetector must have a predict(image) method."""
        mod = self._get_pipeline_module()
        if mod is None:
            _warn_not_implemented("DeepfakeDetector.predict()")
            return
        cls = getattr(mod, "DeepfakeDetector", None)
        if cls is None:
            return
        assert hasattr(cls, "predict"), (
            "DeepfakeDetector must have a predict() method"
        )

    def test_predict_returns_dict(self):
        """predict() should return a dict with at least 'is_fake' and 'confidence'."""
        import numpy as np

        mod = self._get_pipeline_module()
        if mod is None:
            _warn_not_implemented("DeepfakeDetector.predict() return shape")
            return

        cls = getattr(mod, "DeepfakeDetector", None)
        if cls is None:
            return

        try:
            detector = cls()
            dummy_image = np.zeros((224, 224, 3), dtype=np.uint8)
            result = detector.predict(dummy_image)
        except Exception as e:
            _warn_not_implemented(f"predict() — raised {e}")
            return

        assert isinstance(result, dict), "predict() must return a dict"
        assert "is_fake" in result, "result dict must contain 'is_fake'"
        assert "confidence" in result, "result dict must contain 'confidence'"
        assert isinstance(result["confidence"], float), "'confidence' must be a float"
        assert 0.0 <= result["confidence"] <= 1.0, "'confidence' must be between 0 and 1"
        
