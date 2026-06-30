"""Tests for chat provider routing with pro features (key rotation, VM fallback)."""

import unittest
from unittest.mock import patch, MagicMock
from modules import chat_service

class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload

class FakeRequests:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self._is_vm_test = True # For identification in chat_service.py

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise RuntimeError("Unexpected call to requests.post")
        return self.responses.pop(0)

def clock_from(values):
    iterator = iter(values)
    return lambda: next(iterator)

class TestChatProviderPro(unittest.TestCase):

    @patch("modules.vm_relay.get_vm_status")
    def test_key_rotation_openrouter(self, mock_vm_status):
        mock_vm_status.return_value = {"online": False}
        # First key fails, second key succeeds
        client = FakeRequests([
            FakeResponse(401, text="invalid key 1"),
            FakeResponse(200, {"choices": [{"message": {"content": "ok from key 2"}}]})
        ])

        env = {"OPENROUTER_API_KEYS": "key1,key2"}
        result = chat_service.chat(
            "hello",
            env=env,
            requests_client=client,
            clock=clock_from([1.0, 1.1])
        )

        self.assertEqual(result["response"], "ok from key 2")
        self.assertEqual(result["model_used"], "openrouter/google/gemma-3-27b-it:free")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Bearer key1", client.calls[0]["headers"]["Authorization"])
        self.assertIn("Bearer key2", client.calls[1]["headers"]["Authorization"])

    def test_redaction_plural_keys(self):
        env = {"OPENROUTER_API_KEYS": "key1,key2", "GEMINI_API_KEY": "gemkey"}
        detail = "Error with key1 and key2 and gemkey"
        sanitized = chat_service._sanitize_detail(detail, env)
        self.assertEqual(sanitized, "Error with [redacted] and [redacted] and [redacted]")

    @patch("modules.vm_relay.get_vm_status")
    @patch("modules.vm_relay.send_task_to_vm")
    @patch("time.sleep") # Don't actually sleep in tests
    def test_vm_fallback_success(self, mock_sleep, mock_send, mock_status):
        # Gemini fails, OR fails, VM succeeds
        client = FakeRequests([
            FakeResponse(401, text="gemini fail"),
            FakeResponse(401, text="or fail")
        ])

        mock_status.side_effect = [
            {"online": True}, # Initial check
            {"online": True, "recent": []}, # Polling check 1 (not done)
            {"online": True, "recent": [{"task": "chat-fallback-testmark", "status": "done", "result": "hello from vm"}]} # Polling check 2 (done)
        ]

        # In modules/chat_service.py: marker = f"chat-fallback-{uuid.uuid4().hex[:8]}"
        mock_uuid = MagicMock()
        mock_uuid.hex = "testmarkerhex"

        with patch("uuid.uuid4", return_value=mock_uuid):
            result = chat_service.chat(
                "hello",
                env={"GEMINI_API_KEY": "gem", "OPENROUTER_API_KEY": "or"},
                requests_client=client,
                clock=clock_from([1.0, 1.5])
            )

        self.assertEqual(result["response"], "hello from vm")
        self.assertEqual(result["model_used"], "vm/jules-worker")
        mock_send.assert_called_once()
        self.assertIn("chat-fallback-testmark", mock_send.call_args[0][0])

    @patch("modules.vm_relay.get_vm_status")
    def test_health_includes_vm(self, mock_status):
        # All local providers fail, but VM is online
        client = FakeRequests([
            FakeResponse(401, text="gemini fail"),
            FakeResponse(401, text="or fail")
        ])

        mock_status.return_value = {"online": True}

        result = chat_service.test_chat_providers(
            env={"GEMINI_API_KEY": "gem", "OPENROUTER_API_KEY": "or"},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "ok")

if __name__ == "__main__":
    unittest.main()
