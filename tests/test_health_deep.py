import unittest
from unittest.mock import patch, MagicMock
from bridge import app

class TestHealthDeep(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.token = "JULES-SECURE-999"

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_success(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        mock_chat.return_value = {
            "healthy": True,
            "providers": {
                "gemini": {"status": "ok", "ms": 10},
                "openrouter": {"status": "ok", "ms": 20},
                "vm_worker": {"status": "ok", "ms": 5},
            },
        }

        # Mock Pressure
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}

        # Mock Disk
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}

        # Mock GCP
        mock_gcloud.return_value = "ya29.fake"

        # Mock Azure (socket)
        mock_socket.return_value.__enter__.return_value = MagicMock()

        response = self.app.get('/health/deep', headers={"Authorization": f"Bearer {self.token}"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("providers", data)
        self.assertIn("resources", data)
        self.assertEqual(data["providers"]["gemini"]["status"], "pass")
        self.assertEqual(data["providers"]["openrouter"]["status"], "pass")
        self.assertEqual(data["providers"]["vm_worker"]["status"], "pass")
        self.assertEqual(data["providers"]["gcp"]["status"], "pass")
        self.assertEqual(data["providers"]["azure"]["status"], "pass")

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token", return_value="")
    @patch("socket.create_connection", side_effect=OSError("offline"))
    def test_health_deep_maps_chat_failures_truthfully(
        self,
        _mock_socket,
        _mock_gcloud,
        mock_disk,
        mock_pressure,
        mock_chat,
    ):
        mock_chat.return_value = {
            "healthy": False,
            "providers": {
                "gemini": {
                    "status": "error",
                    "code": 400,
                    "error_type": "invalid_key",
                    "detail": "HTTP 400: invalid",
                },
                "openrouter": {
                    "status": "error",
                    "code": 401,
                    "error_type": "invalid_key",
                    "detail": "HTTP 401: user not found",
                },
            },
        }
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}

        response = self.app.get('/health/deep', headers={"Authorization": f"Bearer {self.token}"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["providers"]["gemini"]["status"], "fail")
        self.assertEqual(data["providers"]["gemini"]["code"], 400)
        self.assertEqual(data["providers"]["gemini"]["error_type"], "invalid_key")
        self.assertEqual(data["providers"]["openrouter"]["status"], "fail")
        self.assertEqual(data["providers"]["openrouter"]["code"], 401)
        self.assertEqual(data["providers"]["openrouter"]["error_type"], "invalid_key")

    def test_health_deep_unauthorized(self):
        response = self.app.get('/health/deep')
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
