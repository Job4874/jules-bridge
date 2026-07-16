"""Tests for modules/antigravity_agent.py and /agent/* bridge routes.

All tests run offline (dry_run=True or mocked SDK import).
No google-antigravity SDK binary is required to run this suite.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.antigravity_agent import (
    AgentChatResult,
    AgentPreflightResult,
    AgentStreamResult,
    agent_chat,
    agent_preflight,
    agent_stream,
)


# ---------------------------------------------------------------------------
# agent_preflight()
# ---------------------------------------------------------------------------


class TestAgentPreflight:
    def test_returns_preflight_result_type(self):
        result = agent_preflight()
        assert isinstance(result, AgentPreflightResult)

    def test_never_raises(self):
        """Preflight must always return a dict, never raise."""
        result = agent_preflight()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = agent_preflight()
        assert "ready" in result
        assert "installed" in result
        assert "api_key_present" in result

    def test_not_ready_without_real_key(self):
        """Without a real GEMINI_API_KEY the result should not be ready."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "your-gemini-or-auth-key"}):
            result = agent_preflight()
        # SDK may or may not be installed in CI — either way, key is a placeholder
        assert result["api_key_present"] is False

    def test_ready_false_when_sdk_missing(self):
        """When the SDK is not importable, ready must be False."""
        with patch("modules.antigravity_agent._import_sdk", return_value=(False, "No module named 'google.antigravity'", None, None)):
            result = agent_preflight()
        assert result["ready"] is False
        assert result["installed"] is False
        assert "install_hint" in result

    def test_ready_true_when_sdk_present_and_key_set(self):
        """Simulate the happy path: SDK available + valid key."""
        mock_agent = MagicMock()
        mock_config = MagicMock()
        with patch("modules.antigravity_agent._import_sdk", return_value=(True, "1.0.0", mock_agent, mock_config)):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "real-key-abc123"}):
                result = agent_preflight()
        assert result["installed"] is True
        assert result["api_key_present"] is True
        assert result["ready"] is True


# ---------------------------------------------------------------------------
# agent_chat() — dry_run mode (no SDK needed)
# ---------------------------------------------------------------------------


class TestAgentChatDryRun:
    def test_dry_run_returns_correct_status(self):
        result = agent_chat("hello world", dry_run=True)
        assert isinstance(result, AgentChatResult)
        assert result["status"] == "dry_run"
        assert result["dry_run"] is True

    def test_dry_run_text_is_empty(self):
        result = agent_chat("test prompt", dry_run=True)
        assert result["text"] == ""

    def test_dry_run_contains_preview(self):
        result = agent_chat("test prompt", dry_run=True)
        assert "command_preview" in result

    def test_empty_prompt_returns_error(self):
        result = agent_chat("", dry_run=True)
        assert result["status"] == "error"
        assert "prompt" in result.get("error", "").lower()

    def test_whitespace_prompt_returns_error(self):
        result = agent_chat("   ", dry_run=True)
        assert result["status"] == "error"

    def test_returns_agent_chat_result_type(self):
        result = agent_chat("hi", dry_run=True)
        assert isinstance(result, AgentChatResult)

    def test_never_raises(self):
        with patch("modules.antigravity_agent._import_sdk", side_effect=RuntimeError("boom")):
            result = agent_chat("hi", dry_run=False)
        assert isinstance(result, dict)
        assert result["status"] in ("error", "dry_run", "ok", "timeout")

    def test_sdk_not_installed_returns_error(self):
        with patch("modules.antigravity_agent._import_sdk", return_value=(False, "No module", None, None)):
            result = agent_chat("hello", dry_run=False)
        assert result["status"] == "error"
        assert "SDK not available" in result.get("error", "")

    def test_model_passed_through(self):
        result = agent_chat("hello", model="gemini-2.0-flash-exp", dry_run=True)
        assert result["model"] == "gemini-2.0-flash-exp"


# ---------------------------------------------------------------------------
# agent_stream() — dry_run mode (no SDK needed)
# ---------------------------------------------------------------------------


class TestAgentStreamDryRun:
    def test_dry_run_returns_correct_status(self):
        result = agent_stream("stream me", dry_run=True)
        assert isinstance(result, AgentStreamResult)
        assert result["status"] == "dry_run"
        assert result["dry_run"] is True

    def test_dry_run_tokens_empty(self):
        result = agent_stream("stream me", dry_run=True)
        assert result["tokens"] == []
        assert result["token_count"] == 0

    def test_empty_prompt_returns_error(self):
        result = agent_stream("", dry_run=True)
        assert result["status"] == "error"

    def test_returns_agent_stream_result_type(self):
        result = agent_stream("hello", dry_run=True)
        assert isinstance(result, AgentStreamResult)

    def test_never_raises(self):
        with patch("modules.antigravity_agent._import_sdk", side_effect=Exception("boom")):
            result = agent_stream("hi", dry_run=False)
        assert isinstance(result, dict)

    def test_sdk_not_installed_returns_error(self):
        with patch("modules.antigravity_agent._import_sdk", return_value=(False, "No module", None, None)):
            result = agent_stream("hello", dry_run=False)
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Bridge route tests  (/agent/*)
# ---------------------------------------------------------------------------


class TestAgentBridgeRoutes(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("BRIDGE_TOKEN", "JULES-SECURE-999")
        import bridge  # noqa: PLC0415
        bridge.app.config["TESTING"] = True
        self.client = bridge.app.test_client()
        self.headers = {
            "Authorization": "Bearer JULES-SECURE-999",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: dict) -> dict:
        resp = self.client.post(path, data=json.dumps(body), headers=self.headers)
        return resp.get_json() or {}

    # /agent/preflight

    def test_preflight_returns_200(self):
        resp = self.client.post("/agent/preflight", data="{}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_preflight_has_ready_key(self):
        body = self._post("/agent/preflight", {})
        self.assertIn("ready", body)

    def test_preflight_has_installed_key(self):
        body = self._post("/agent/preflight", {})
        self.assertIn("installed", body)

    # /agent/chat dry_run

    def test_chat_dry_run_true_by_default(self):
        body = self._post("/agent/chat", {"prompt": "hello"})
        self.assertEqual(body.get("status"), "dry_run")

    def test_chat_dry_run_explicit_true(self):
        body = self._post("/agent/chat", {"prompt": "hello", "dry_run": True})
        self.assertEqual(body.get("status"), "dry_run")
        self.assertTrue(body.get("dry_run"))

    def test_chat_empty_prompt_returns_error(self):
        # string_field raises BridgeHTTPError(400) when prompt is empty string
        resp = self.client.post(
            "/agent/chat",
            data=json.dumps({"prompt": ""}),
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_chat_missing_prompt_raises_400(self):
        resp = self.client.post("/agent/chat", data="{}", headers=self.headers)
        # string_field raises BridgeHTTPError(400) when required field is missing
        self.assertEqual(resp.status_code, 400)

    def test_chat_returns_model_field(self):
        body = self._post("/agent/chat", {"prompt": "hi", "model": "gemini-2.0-flash-exp"})
        self.assertEqual(body.get("model"), "gemini-2.0-flash-exp")

    # /agent/stream dry_run

    def test_stream_dry_run_true_by_default(self):
        body = self._post("/agent/stream", {"prompt": "stream this"})
        self.assertEqual(body.get("status"), "dry_run")

    def test_stream_tokens_empty_on_dry_run(self):
        body = self._post("/agent/stream", {"prompt": "stream this", "dry_run": True})
        self.assertEqual(body.get("tokens"), [])
        self.assertEqual(body.get("token_count"), 0)

    def test_stream_missing_prompt_raises_400(self):
        resp = self.client.post("/agent/stream", data="{}", headers=self.headers)
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
