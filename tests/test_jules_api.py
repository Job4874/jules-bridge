"""Tests for modules/jules_api.py."""

import json
import unittest
from unittest.mock import patch

from modules import jules_api


class FakeHTTPResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload or {}

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestJulesApi(unittest.TestCase):
    def test_rest_api_enabled_requires_key_and_flag(self):
        self.assertFalse(jules_api.is_rest_api_enabled({"JULES_USE_REST_API": "1"}))
        self.assertTrue(
            jules_api.is_rest_api_enabled(
                {"JULES_API_KEY": "AQ.test-key", "JULES_USE_REST_API": "1"}
            )
        )

    def test_preflight_missing_key(self):
        result = jules_api.jules_api_preflight(api_key="")
        self.assertFalse(result["ready"])
        self.assertEqual(result["likely_blocker"], "missing_api_key")

    def test_sessions_to_stdout_formats_cli_like_lines(self):
        stdout = jules_api.sessions_to_stdout(
            [{"id": "31415926535897932384", "title": "Boba App", "status": "In Progress"}]
        )
        self.assertIn("31415926535897932384", stdout)
        self.assertIn("Boba App", stdout)

    @patch("modules.jules_api.urllib.request.urlopen")
    def test_list_sources_success(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            payload={"sources": [{"name": "sources/github/Job4874/jules-bridge"}]}
        )
        result = jules_api.list_sources(api_key="AQ.test-key")
        self.assertEqual(result["status"], "ok")
        self.assertIn("sources/github/Job4874/jules-bridge", result.get("source_names", []))

    @patch("modules.jules_api.urllib.request.urlopen")
    def test_preflight_sources_are_bounded(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            payload={
                "sources": [
                    {
                        "name": "sources/github/Job4874/jules-bridge",
                        "githubRepo": {"branches": [{"displayName": "main"}]},
                    }
                ]
            }
        )
        result = jules_api.jules_api_preflight(
            api_key="AQ.test-key",
            source="sources/github/Job4874/jules-bridge",
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["sources"]["source_count"], 1)
        self.assertNotIn("payload", result["sources"])

    @patch("modules.jules_api.urllib.request.urlopen")
    def test_create_session_success(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            payload={"id": "12345678901234567890", "title": "Packet run"}
        )
        result = jules_api.create_session(
            prompt="Fix the bridge",
            source="sources/github/Job4874/jules-bridge",
            api_key="AQ.test-key",
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result.get("session_ids"), ["12345678901234567890"])


if __name__ == "__main__":
    unittest.main()
