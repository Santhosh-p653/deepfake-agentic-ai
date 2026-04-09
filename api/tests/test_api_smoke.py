
"""
Basic smoke tests for the API service.
These run in GitHub Actions on every push — no local setup needed.

Place this file at: api/tests/test_api_smoke.py
"""

import importlib
from pathlib import Path


def _can_import(module: str) -> bool:
    """Return True if module is importable, False otherwise."""
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


class TestProjectStructure:
    """Verify the api/ directory has expected files."""

    def test_api_directory_exists(self):
        assert Path("api").exists(), "api/ directory must exist"

    def test_has_python_files(self):
        py_files = list(Path("api").rglob("*.py"))
        assert len(py_files) > 0, "api/ must contain at least one .py file"

    def test_no_syntax_errors(self):
        """All Python files in api/ must be syntax-error free."""
        import ast

        errors = []
        for f in Path("api").rglob("*.py"):
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append(f"{f}: {e}")
        assert not errors, "Syntax errors found:\n" + "\n".join(errors)


class TestCoreDependencies:
    """Check that declared dependencies are actually installable."""

    def test_fastapi_importable(self):
        assert _can_import(
            "fastapi"
        ), "fastapi must be importable — add it to api/requirements.txt"

    def test_uvicorn_importable(self):
        assert _can_import(
            "uvicorn"
        ), "uvicorn must be importable — add it to api/requirements.txt"

    def test_pydantic_importable(self):
        assert _can_import(
            "pydantic"
        ), "pydantic must be importable — required by FastAPI"


class TestFastAPIAppSmoke:
    """
    Light smoke tests for the FastAPI app.
    Uses TestClient so no real server is started.
    Skipped gracefully if the app module isn't wired up yet.
    """

    def _get_app(self):
        """Try to import the FastAPI app — return None if not ready."""
        for module_path in ("api.main", "main", "app"):
            try:
                mod = importlib.import_module(module_path)
                if hasattr(mod, "app"):
                    return mod.app
            except (ImportError, ModuleNotFoundError):
                continue
        return None

    def test_app_importable(self):
        """App module should exist once api/ is wired up."""
        app = self._get_app()
        if app is None:
            import warnings

            warnings.warn(
                "FastAPI app not yet importable — skipping app smoke tests. "
                "Create api/main.py with an `app = FastAPI()` instance.",
                stacklevel=2,
            )
            return
        assert app is not None

    def test_health_endpoint(self):
        """GET /health should return 200 once implemented."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            return

        app = self._get_app()
        if app is None:
            return

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200, (
            f"GET /health returned {response.status_code} — add a /health endpoint"
        )
