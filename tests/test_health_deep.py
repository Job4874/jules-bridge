import unittest
from unittest.mock import patch, MagicMock
from bridge import app

class TestHealthDeep(unittest.TestCase):
    def setUp(self):
        # bridge reads BRIDGE_TOKEN at import time — patch the module-level variable directly
        self.token_patcher = patch("bridge.BRIDGE_TOKEN", "testtoken")
        self.token_patcher.start()
        self.app = app.test_client()
        self.app.testing = True
        self.token = "testtoken"

    @patch("modules.health_service.test_chat_providers")
    @patch("modules.health_service.detect_resource_pressure")
    @patch("modules.health_service.get_disk_usage")
    @patch("modules.health_service._check_gcp")
    @patch("socket.create_connection")
    def test_health_deep_success(self, mock_socket, mock_gcp, mock_disk, mock_pressure, mock_chat):
        # Mock model loop
        mock_chat.return_value = {
            "healthy": True,
            "providers": {"vm": {"status": "ok", "model": "jules-worker"}},
        }

        # Mock Pressure
        mock_pressure.return_value = {"cpu_percent": 10.0, "memory_percent": 20.0, "maxed_out": False}

        # Mock Disk
        mock_disk.return_value = {"percent": 50.0, "free_gb": 100}

        # Mock GCP
        mock_gcp.return_value = {"status": "pass", "ms": 1, "detail": "gcloud token active"}

        # Mock Azure (socket)
        mock_socket.return_value.__enter__.return_value = MagicMock()

        response = self.app.get('/health/deep', headers={"Authorization": f"Bearer {self.token}"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("providers", data)
        self.assertIn("resources", data)
        self.assertTrue(data["keyless_mode"])
        self.assertEqual(data["model_loop_mode"], "vm_browser")
        self.assertEqual(data["providers"]["model_loop"]["status"], "pass")
        self.assertEqual(data["providers"]["gcp"]["status"], "pass")
        self.assertEqual(data["providers"]["azure"]["status"], "pass")

    def test_health_deep_unauthorized(self):
        response = self.app.get('/health/deep')
        self.assertEqual(response.status_code, 401)

    def tearDown(self):
        self.token_patcher.stop()


class TestCheckGCP(unittest.TestCase):
    @patch('subprocess.run')
    def test_gcp_fallback_success_on_second(self, mock_run):
        from modules.health_service import _check_gcp
        # First call raises an exception (e.g. FileNotFoundError)
        # Second call succeeds
        mock_run.side_effect = [
            Exception("Command not found"),
            MagicMock(returncode=0, stdout="fake_token\n")
        ]

        result = _check_gcp()

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["detail"], "gcloud token active")
        self.assertEqual(mock_run.call_count, 2)

        self.assertEqual(mock_run.call_args_list[0][0][0], ["gcloud", "auth", "print-access-token"])
        self.assertEqual(mock_run.call_args_list[1][0][0], ["gcloud.cmd", "auth", "print-access-token"])

    @patch('subprocess.run')
    def test_gcp_fallback_all_fail(self, mock_run):
        from modules.health_service import _check_gcp
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout="")
        ]

        result = _check_gcp()

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["detail"], "No active gcloud session")
        self.assertEqual(mock_run.call_count, 2)



if __name__ == "__main__":
    unittest.main()
