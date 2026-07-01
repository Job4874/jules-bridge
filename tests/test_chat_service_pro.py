"""Tests for chat provider routing with pro features (VM fallback)."""

import unittest
from unittest.mock import patch, MagicMock
from modules import chat_service

class FakeRequests:
    def __init__(self, responses=None):
        self.responses = list(responses) if responses else []
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
    @patch("modules.vm_relay.send_task_to_vm")
    @patch("time.sleep") # Don't actually sleep in tests
    def test_vm_fallback_success(self, mock_sleep, mock_send, mock_status):
        client = FakeRequests([])

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
                env={},
                requests_client=client,
                clock=clock_from([1.0, 1.5])
            )

        self.assertEqual(result["response"], "hello from vm")
        self.assertEqual(result["model_used"], "vm/jules-worker")
        mock_send.assert_called_once()
        self.assertIn("chat-fallback-testmark", mock_send.call_args[0][0])

    @patch("modules.vm_relay.get_vm_status")
    def test_health_includes_vm(self, mock_status):
        client = FakeRequests([])

        mock_status.return_value = {"online": True}

        result = chat_service.test_chat_providers(
            env={},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "ok")

    @patch("modules.vm_relay.get_vm_status")
    def test_health_marks_vm_degraded_when_recent_chat_exhausted(self, mock_status):
        client = FakeRequests([])
        exhausted = (
            "No LLM available - GEMINI_API_KEY is rate-limited and all "
            "OpenRouter free models failed. Check ~/.jules_worker.env"
        )
        mock_status.return_value = {
            "online": True,
            "recent": [
                {
                    "task": "[chat-fallback-deadbeef] flash fast",
                    "status": "done",
                    "result": exhausted,
                }
            ],
        }

        result = chat_service.test_chat_providers(
            env={},
            requests_client=client,
            clock=clock_from([1.0, 1.1]),
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "degraded")
        self.assertIn("No LLM available", result["providers"]["vm"]["detail"])

if __name__ == "__main__":
    unittest.main()
