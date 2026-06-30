"""Tests for chat provider routing."""

import unittest
from unittest.mock import patch

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

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def clock_from(values):
    iterator = iter(values)
    return lambda: next(iterator)


class TestChatProviderHealth(unittest.TestCase):
    def setUp(self):
        chat_service._last_vm_success = 0.0

    @patch("modules.vm_relay.get_vm_status")
    def test_no_keys_reports_provider_gaps_without_requests(self, mock_vm_status):
        mock_vm_status.return_value = {"online": False}
        result = chat_service.test_chat_providers(env={}, requests_client=FakeRequests([]))

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "no_key")
        self.assertEqual(result["providers"]["openrouter"]["status"], "no_key")
        self.assertEqual(result["providers"]["vm_worker"]["status"], "offline")

    @patch("modules.vm_relay.get_vm_status")
    def test_gemini_health_success_redacts_from_result_shape(self, mock_vm_status, mock_requests=None):
        mock_vm_status.return_value = {"online": False}
        client = FakeRequests([FakeResponse(200)])

        result = chat_service.test_chat_providers(
            env={"GEMINI_API_KEY": "secret-key"},
            requests_client=client,
            clock=clock_from([1.0, 1.025, 1.030]),
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "ok")
        self.assertEqual(result["providers"]["gemini"]["ms"], 24)
        self.assertNotIn("secret-key", str(result))

    @patch("modules.vm_relay.get_vm_status")
    def test_vm_health_reports_recent_success_on_flaky_probe(self, mock_vm_status):
        # Reset global success evidence for testing
        chat_service._last_vm_success = 0.0

        # 1. Failed probe, no success evidence
        mock_vm_status.return_value = {"online": True, "gemini": False, "openrouter": False}
        result = chat_service.test_chat_providers(env={}, clock=clock_from([1000.0]))
        self.assertEqual(result["providers"]["vm_worker"]["status"], "fail")

        # 2. Record a success
        chat_service._last_vm_success = 1000.0

        # 3. Flaky probe with recent success evidence should report 'ok'
        result = chat_service.test_chat_providers(env={}, clock=clock_from([1010.0]))
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")
        self.assertIn("recent success", result["providers"]["vm_worker"]["detail"])

    @patch("modules.vm_relay.get_vm_status")
    def test_vm_health_reports_fail_after_ttl_expires(self, mock_vm_status):
        # 1. Success evidence at T=1000
        chat_service._last_vm_success = 1000.0

        # 2. Probe fails at T=1000 + TTL + 1
        mock_vm_status.return_value = {"online": True, "gemini": False, "openrouter": False}
        clock_val = 1000.0 + chat_service._VM_SUCCESS_TTL + 1.0
        result = chat_service.test_chat_providers(env={}, clock=clock_from([clock_val]))

        self.assertEqual(result["providers"]["vm_worker"]["status"], "fail")


class TestChatCompletion(unittest.TestCase):
    def test_chat_uses_gemini_when_available(self):
        client = FakeRequests(
            [
                FakeResponse(
                    200,
                    {"candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}]},
                )
            ]
        )

        result = chat_service.chat(
            "hello",
            image_base64="abc123",
            history=[{"role": "assistant", "content": "prior"}],
            env={"GEMINI_API_KEY": "gem-secret"},
            requests_client=client,
            clock=clock_from([10.0, 10.5]),
        )

        self.assertEqual(result["response"], "hello from gemini")
        self.assertEqual(result["model_used"], "gemini-2.0-flash")
        self.assertEqual(result["elapsed_ms"], 500)
        payload = client.calls[0]["json"]
        self.assertEqual(payload["contents"][-1]["parts"][1]["inline_data"]["data"], "abc123")
        self.assertNotIn("gem-secret", str(result))

    def test_chat_falls_back_to_openrouter_and_redacts_errors(self):
        client = FakeRequests(
            [
                FakeResponse(429, text="quota hit for gem-secret"),
                FakeResponse(200, {"choices": [{"message": {"content": "openrouter ok"}}]}),
            ]
        )

        result = chat_service.chat(
            "hello",
            model_alias="smart",
            env={"GEMINI_API_KEY": "gem-secret", "OPENROUTER_API_KEY": "or-secret"},
            requests_client=client,
            clock=clock_from([1.0, 1.2]),
        )

        self.assertEqual(result["response"], "openrouter ok")
        self.assertEqual(result["model_used"], "openrouter/deepseek/deepseek-r1:free")
        self.assertNotIn("gem-secret", str(result))
        self.assertNotIn("or-secret", str(result))

    def test_chat_offline_redacts_provider_errors(self):
        client = FakeRequests(
            [
                FakeResponse(429, text="quota hit for gem-secret"),
                FakeResponse(500, text="router failed for or-secret"),
            ]
        )

        result = chat_service.chat(
            "hello",
            env={"GEMINI_API_KEY": "gem-secret", "OPENROUTER_API_KEY": "or-secret"},
            requests_client=client,
            clock=clock_from([1.0, 1.2]),
        )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("Gemini 429", result["errors"][0])
        self.assertIn("OpenRouter 500", result["errors"][1])
        self.assertNotIn("gem-secret", str(result))
        self.assertNotIn("or-secret", str(result))

    def test_chat_offline_response_is_stable(self):
        result = chat_service.chat(
            "hello",
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.0]),
        )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("offline", result["response"])
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
