import unittest
from unittest.mock import patch, MagicMock
import os
from modules.health_service import get_deep_health

class TestHealthDeep(unittest.TestCase):

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_success(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        # Mock Chat
        mock_chat.return_value = {
            "healthy": True,
            "providers": {
                "gemini": {"status": "ok", "model": "gemini-2.0-flash", "ms": 10},
                "openrouter": {"status": "ok", "model": "google/gemma-3-27b-it:free", "ms": 10}
            }
        }

        # Mock Pressure
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}

        # Mock Disk
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}

        # Mock GCP
        mock_gcloud.return_value = "ya29.fake"

        # Mock Azure (socket)
        mock_socket.return_value.__enter__.return_value = MagicMock()

        data = get_deep_health()

        self.assertEqual(data["status"], "ok")
        self.assertIn("providers", data)
        self.assertIn("resources", data)
        self.assertEqual(data["providers"]["gcp"]["status"], "pass")
        self.assertEqual(data["providers"]["azure"]["status"], "pass")
        self.assertEqual(data["providers"]["gemini"]["status"], "pass")

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_invalid_keys(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        # Mock providers failing
        mock_chat.return_value = {
            "healthy": False,
            "providers": {
                "gemini": {"status": "error", "code": 401, "detail": "User not found", "ms": 10},
                "openrouter": {"status": "error", "code": 401, "detail": "Invalid API key", "ms": 10}
            }
        }
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}
        mock_gcloud.return_value = "ya29.fake"
        mock_socket.return_value.__enter__.return_value = MagicMock()

        data = get_deep_health()

        self.assertEqual(data["providers"]["gemini"]["status"], "fail")
        self.assertEqual(data["providers"]["openrouter"]["status"], "fail")

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_one_provider_ok(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        # Mock one provider passing
        mock_chat.return_value = {
            "healthy": True,
            "providers": {
                "gemini": {"status": "ok", "model": "gemini-2.0-flash", "ms": 10},
                "openrouter": {"status": "no_key", "detail": "OPENROUTER_API_KEY not set"}
            }
        }
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}
        mock_gcloud.return_value = "ya29.fake"
        mock_socket.return_value.__enter__.return_value = MagicMock()

        data = get_deep_health()

        self.assertEqual(data["providers"]["gemini"]["status"], "pass")
        self.assertEqual(data["providers"]["openrouter"]["status"], "keyless")

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.reasoning_module._gcloud_access_token")
    @patch("socket.create_connection")
    def test_health_deep_keyless_mode(self, mock_socket, mock_gcloud, mock_disk, mock_pressure, mock_chat):
        # Mock no keys
        mock_chat.return_value = {
            "healthy": False,
            "providers": {
                "gemini": {"status": "no_key", "detail": "GEMINI_API_KEY not set"},
                "openrouter": {"status": "no_key", "detail": "OPENROUTER_API_KEY not set"}
            }
        }
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}
        mock_gcloud.return_value = ""
        mock_socket.side_effect = Exception("offline")

        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            data = get_deep_health()

        self.assertTrue(data["keyless_mode"])
        self.assertEqual(data["providers"]["gemini"]["status"], "keyless")
        self.assertEqual(data["providers"]["openrouter"]["status"], "keyless")
        self.assertEqual(data["providers"]["gcp"]["status"], "fail")
        self.assertEqual(data["providers"]["azure"]["status"], "fail")

if __name__ == "__main__":
    unittest.main()
