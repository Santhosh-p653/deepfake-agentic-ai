import unittest
from unittest.mock import MagicMock, patch
import requests

from ui.api_client import APIClient


class TestAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = APIClient(base_url="http://testserver:8000")

    def test_init_default_and_custom(self):
        client_custom = APIClient(base_url="http://custom:9000/")
        self.assertEqual(client_custom.base_url, "http://custom:9000")

        with patch.dict("os.environ", {"API_URL": "http://envserver:8000/"}):
            client_env = APIClient()
            self.assertEqual(client_env.base_url, "http://envserver:8000")

    @patch("ui.api_client.requests.get")
    def test_check_health_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "database": "connected"}
        mock_get.return_value = mock_resp

        ok, data = self.client.check_health()
        self.assertTrue(ok)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")
        mock_get.assert_called_once_with("http://testserver:8000/health", timeout=15)

    @patch("ui.api_client.requests.get")
    def test_check_health_service_unavailable(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"
        mock_get.return_value = mock_resp

        ok, data = self.client.check_health()
        self.assertFalse(ok)
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["status_code"], 503)

    @patch("ui.api_client.requests.get")
    def test_check_health_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        ok, data = self.client.check_health()
        self.assertFalse(ok)
        self.assertEqual(data["status"], "unreachable")
        self.assertIn("Connection refused", data["error"])

    @patch("ui.api_client.requests.get")
    def test_ping(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        self.assertTrue(self.client.ping())

        mock_get.side_effect = requests.exceptions.Timeout("Timed out")
        self.assertFalse(self.client.ping())

    @patch("ui.api_client.requests.post")
    def test_upload_media_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "accepted",
            "id": 42,
            "filename": "face.jpg",
            "size_mb": 0.123,
            "minio_object": "hash123.jpg",
        }
        mock_post.return_value = mock_resp

        ok, data = self.client.upload_media("face.jpg", b"fake_bytes")
        self.assertTrue(ok)
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["status"], "accepted")
        mock_post.assert_called_once()

    @patch("ui.api_client.requests.post")
    def test_upload_media_validation_rejection(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"status": "rejected", "reason": "Invalid format"}
        mock_post.return_value = mock_resp

        ok, data = self.client.upload_media("face.txt", b"plain_text")
        self.assertFalse(ok)
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["reason"], "Invalid format")

    @patch("ui.api_client.requests.get")
    def test_get_result_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 42,
            "filename": "face.jpg",
            "status": "completed",
            "verdict": "REAL",
            "verdict_score": 0.12,
        }
        mock_get.return_value = mock_resp

        ok, data = self.client.get_result(42)
        self.assertTrue(ok)
        self.assertEqual(data["verdict"], "REAL")

    @patch("ui.api_client.requests.get")
    def test_get_result_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        ok, data = self.client.get_result(999)
        self.assertFalse(ok)
        self.assertEqual(data["status"], "not_found")

    @patch("ui.api_client.time.sleep", return_value=None)
    @patch.object(APIClient, "get_result")
    def test_poll_result_success(self, mock_get_result, mock_sleep):
        # First call: processing; Second call: completed
        mock_get_result.side_effect = [
            (True, {"id": 1, "status": "processing"}),
            (True, {"id": 1, "status": "completed", "verdict": "DEEPFAKE", "verdict_score": 0.94}),
        ]

        callbacks = []
        def status_cb(st, data):
            callbacks.append(st)

        ok, data = self.client.poll_result(1, timeout_sec=10, interval_sec=0.01, status_callback=status_cb)
        self.assertTrue(ok)
        self.assertEqual(data["verdict"], "DEEPFAKE")
        self.assertIn("processing", callbacks)
        self.assertIn("completed", callbacks)

    @patch("ui.api_client.time.sleep", return_value=None)
    @patch.object(APIClient, "get_result")
    def test_poll_result_timeout(self, mock_get_result, mock_sleep):
        mock_get_result.return_value = (True, {"id": 2, "status": "processing"})

        # Setting timeout_sec to a negative/zero threshold triggers instant timeout
        with patch("ui.api_client.time.time", side_effect=[0, 100]):
            ok, data = self.client.poll_result(2, timeout_sec=5, interval_sec=0.01)
            self.assertFalse(ok)
            self.assertEqual(data["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
