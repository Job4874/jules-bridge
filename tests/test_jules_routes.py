"""Tests for modules/jules_routes.py Blueprint endpoints."""
import json
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask
from modules.jules_routes import jules_bp


class TestJulesRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(jules_bp, url_prefix="/jules")
        self.app.testing = True
        self.client = self.app.test_client()

    @patch("modules.build_dispatch")
    def test_dispatch_success_with_content(self, mock_dispatch):
        mock_dispatch.return_value = {"status": "ok", "packets": []}
        res = self.client.post("/jules/dispatch", json={"content": "test dump"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")
        mock_dispatch.assert_called_once()

    @patch("modules.build_dispatch")
    def test_dispatch_success_with_data(self, mock_dispatch):
        mock_dispatch.return_value = {"status": "ok", "packets": []}
        res = self.client.post("/jules/dispatch", json={"data": "test dump data"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    @patch("modules.build_dispatch")
    def test_dispatch_error_status(self, mock_dispatch):
        mock_dispatch.return_value = {"error": "Invalid format", "status": "failed"}
        res = self.client.post("/jules/dispatch", json={"content": "bad data"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"], "Invalid format")

    def test_dispatch_invalid_statuses_type(self):
        res = self.client.post("/jules/dispatch", json={"include_statuses": 12345})
        self.assertEqual(res.status_code, 400)
        self.assertIn("include_statuses must be a string or list", res.get_json()["details"])

    @patch("modules.launch_packets")
    def test_launch_success(self, mock_launch):
        mock_launch.return_value = {"status": "ok", "launched": 2}
        res = self.client.post("/jules/launch", json={"dry_run": True})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["launched"], 2)

    def test_launch_invalid_packet_files(self):
        res = self.client.post("/jules/launch", json={"packet_files": "not-a-list"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("packet_files must be a list of strings", res.get_json()["details"])

    def test_launch_invalid_force_packet_files(self):
        res = self.client.post("/jules/launch", json={"force_packet_files": [123]})
        self.assertEqual(res.status_code, 400)
        self.assertIn("force_packet_files must be a list of strings", res.get_json()["details"])

    @patch("modules.list_remote_sessions")
    def test_sessions_success(self, mock_list):
        mock_list.return_value = {"status": "ok", "sessions": []}
        res = self.client.post("/jules/sessions", json={"dry_run": True})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["sessions"], [])

    @patch("modules.jules_preflight")
    def test_preflight_success(self, mock_preflight):
        mock_preflight.return_value = {"status": "ok", "cli_found": True}
        res = self.client.post("/jules/preflight", json={})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["cli_found"])

    @patch("modules.jules_preflight")
    def test_preflight_error(self, mock_preflight):
        mock_preflight.return_value = {"error": "CLI missing", "status": "failed"}
        res = self.client.post("/jules/preflight", json={})
        self.assertEqual(res.status_code, 400)

    @patch("modules.pull_remote_session")
    def test_pull_success(self, mock_pull):
        mock_pull.return_value = {"status": "ok", "session_id": "sess-123"}
        res = self.client.post("/jules/pull", json={"session_id": "sess-123"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["session_id"], "sess-123")

    def test_pull_missing_session_id(self):
        res = self.client.post("/jules/pull", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("session_id is required", res.get_json()["details"])

    @patch("modules.build_cot_ledger")
    def test_cot_success(self, mock_cot):
        mock_cot.return_value = {"status": "ok", "ledger_path": "COT.md"}
        res = self.client.post("/jules/cot", json={})
        self.assertEqual(res.status_code, 200)

    @patch("modules.run_jules_cycle")
    def test_cycle_success(self, mock_cycle):
        mock_cycle.return_value = {"status": "ok", "cycle": 1}
        res = self.client.post("/jules/cycle", json={"content": "test"})
        self.assertEqual(res.status_code, 200)

    def test_cycle_invalid_session_ids(self):
        res = self.client.post("/jules/cycle", json={"session_ids": "not-a-list"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("session_ids must be a list of strings", res.get_json()["details"])

    @patch("modules.run_jules_watch")
    def test_watch_success(self, mock_watch):
        mock_watch.return_value = {"status": "ok", "progressed": True}
        res = self.client.post("/jules/watch", json={})
        self.assertEqual(res.status_code, 200)

    @patch("modules.run_jules_fleet")
    def test_fleet_success(self, mock_fleet):
        mock_fleet.return_value = {"status": "ok", "active": 2}
        res = self.client.post("/jules/fleet", json={})
        self.assertEqual(res.status_code, 200)

    @patch("modules.run_jules_fleet_watch")
    def test_fleet_watch_success(self, mock_fleet_watch):
        mock_fleet_watch.return_value = {"status": "ok", "watched": True}
        res = self.client.post("/jules/fleet-watch", json={})
        self.assertEqual(res.status_code, 200)
