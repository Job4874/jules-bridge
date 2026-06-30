"""Tests for chat provider routing."""

import unittest

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
    def test_no_keys_reports_provider_gaps_without_requests(self):
        result = chat_service.test_chat_providers(env={}, requests_client=FakeRequests([]))

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "no_key")
        self.assertEqual(result["providers"]["openrouter"]["status"], "no_key")

    def test_gemini_health_success_redacts_from_result_shape(self):
        client = FakeRequests([FakeResponse(200)])

        result = chat_service.test_chat_providers(
            env={"GEMINI_API_KEY": "secret-key"},
            requests_client=client,
            clock=clock_from([1.0, 1.025]),
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "ok")
        self.assertEqual(result["providers"]["gemini"]["ms"], 24)
        self.assertNotIn("secret-key", str(result))


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
        self.assertIn("Gemini 429 [quota_limit]", result["errors"][0])
        # OpenRouter will try fallbacks, so we expect multiple error entries
        self.assertIn("OpenRouter 500 [transient_error]", str(result["errors"]))
        self.assertNotIn("gem-secret", str(result))
        self.assertNotIn("or-secret", str(result))

    def test_chat_offline_response_is_stable(self):
        result = chat_service.chat(
            "hello",
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.0]),
            enable_vm_fallback=False,
        )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("offline", result["response"])
        self.assertEqual(result["errors"], [])

    def test_classify_error(self):
        from modules.chat_service import _classify_error
        self.assertEqual(_classify_error(401, "unauthorized"), "invalid_key")
        self.assertEqual(_classify_error(403, "forbidden"), "invalid_key")
        self.assertEqual(_classify_error(429, "too many requests"), "quota_limit")
        self.assertEqual(_classify_error(200, "quota hit"), "quota_limit")
        self.assertEqual(_classify_error(404, "not found"), "model_unavailable")
        self.assertEqual(_classify_error(500, "server error"), "transient_error")
        self.assertEqual(_classify_error(400, "bad request"), "other_error")

    def test_openrouter_model_fallback(self):
        # 1st model fails with 404, 2nd model succeeds
        client = FakeRequests([
            FakeResponse(404, text="model not found"),
            FakeResponse(200, {"choices": [{"message": {"content": "fallback success"}}]})
        ])

        result = chat_service.chat(
            "hello",
            env={"OPENROUTER_API_KEY": "or-key"},
            requests_client=client,
            enable_vm_fallback=False
        )

        self.assertEqual(result["response"], "fallback success")
        self.assertIn("openrouter/", result["model_used"])
        # No 'errors' key in result when success=True, they are logged but not returned in ChatResult


if __name__ == "__main__":
    unittest.main()
