"""Tests for modules/jules_api.py."""

import json
import unittest
from io import BytesIO
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
    def test_use_rest_api_requires_key(self):
        self.assertFalse(jules_api.use_rest_api({"JULES_USE_REST_API": "1"}))
        self.assertTrue(
            jules_api.use_rest_api({"JULES_API_KEY": "AQ.test-key", "JULES_USE_REST_API": "1"})
        )

    def test_sessions_stdout_formats_cli_like_lines(self):
        stdout = jules_api.sessions_stdout(
            {
                "sessions": [
                    {
                        "id": "31415926535897932384",
                        "title": "Boba App",
                        "state": "STATE_RUNNING",
                    }
                ]
            }
        )
        self.assertIn("31415926535897932384", stdout)
        self.assertIn("In Progress", stdout)

    @patch("modules.jules_api.request.urlopen")
    def test_list_sources_success(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            payload={"sources": [{"name": "sources/github/Job4874/jules-bridge"}]}
        )
        result = jules_api.list_sources(env={"JULES_API_KEY": "AQ.test-key"})
        self.assertTrue(result["ok"])
        self.assertIn("sources/github/Job4874/jules-bridge", result["stdout"])

    @patch("modules.jules_api.request.urlopen")
    def test_create_session_success(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            payload={"id": "12345678901234567890", "title": "Packet run"}
        )
        result = jules_api.create_session(
            prompt="Fix the bridge",
            source="sources/github/Job4874/jules-bridge",
            env={"JULES_API_KEY": "AQ.test-key"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["session_ids"], ["12345678901234567890"])


if __name__ == "__main__":
    unittest.main()
