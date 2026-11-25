import os
import time
from typing import Any, Callable, Dict, Optional, Tuple
import requests


class APIClient:
    """Client for communicating with the Deepfake Agentic AI FastAPI backend."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 15):
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = os.getenv("API_URL", "http://api:8000").rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Check API service and database connectivity."""
        url = f"{self.base_url}/health"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return True, resp.json()
            return False, {"status": "error", "status_code": resp.status_code, "data": resp.text}
        except requests.exceptions.RequestException as exc:
            return False, {"status": "unreachable", "error": str(exc)}

    def ping(self) -> bool:
        """Simple liveness probe."""
        url = f"{self.base_url}/ping"
        try:
            resp = requests.get(url, timeout=self.timeout)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def upload_media(self, filename: str, file_bytes: bytes) -> Tuple[bool, Dict[str, Any]]:
        """Upload a media file (image/video) for deepfake analysis.

        Returns (success: bool, response_json_or_error: dict).
        """
        url = f"{self.base_url}/upload"
        files = {"file": (filename, file_bytes)}
        try:
            resp = requests.post(url, files=files, timeout=60)
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            if resp.status_code == 200 and data.get("status") == "accepted":
                return True, data
            return False, data
        except requests.exceptions.RequestException as exc:
            return False, {"status": "error", "reason": f"Connection error: {str(exc)}"}

    def get_result(self, record_id: int) -> Tuple[bool, Dict[str, Any]]:
        """Fetch result for a given record ID."""
        url = f"{self.base_url}/result/{record_id}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return True, resp.json()
            elif resp.status_code == 404:
                return False, {"status": "not_found", "reason": "Record ID not found"}
            else:
                return False, {"status": "error", "reason": f"HTTP {resp.status_code}: {resp.text}"}
        except requests.exceptions.RequestException as exc:
            return False, {"status": "error", "reason": str(exc)}

    def poll_result(
        self,
        record_id: int,
        timeout_sec: int = 60,
        interval_sec: float = 1.5,
        status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Poll /result/{record_id} until completed, failed, or timed out."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            success, data = self.get_result(record_id)
            if not success:
                if status_callback:
                    status_callback("polling_error", data)
                time.sleep(interval_sec)
                continue

            current_status = data.get("status")
            if status_callback:
                status_callback(current_status, data)

            if current_status == "completed":
                return True, data
            elif current_status in ("failed", "deleted"):
                return False, data

            time.sleep(interval_sec)

        return False, {
            "status": "timeout",
            "reason": f"Polling timed out after {timeout_sec}s before completion.",
            "last_record_id": record_id,
        }
