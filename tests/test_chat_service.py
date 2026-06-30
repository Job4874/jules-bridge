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
        chat_service._LAST_VM_CHAT_FAILURE.clear()
        chat_service._LAST_VM_CHAT_SUCCESS.clear()

    def tearDown(self):
        chat_service._LAST_VM_CHAT_FAILURE.clear()
        chat_service._LAST_VM_CHAT_SUCCESS.clear()

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
    def setUp(self):
        chat_service._LAST_VM_CHAT_FAILURE.clear()
        chat_service._LAST_VM_CHAT_SUCCESS.clear()

    def tearDown(self):
        chat_service._LAST_VM_CHAT_FAILURE.clear()
        chat_service._LAST_VM_CHAT_SUCCESS.clear()

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
        self.assertIn("OpenRouter 500 [transient_error]", result["errors"][1])
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

    def test_chat_rotates_plural_openrouter_keys(self):
        client = FakeRequests(
            [
                FakeResponse(401, text="router failed for plural-a"),
                FakeResponse(200, {"choices": [{"message": {"content": "openrouter ok"}}]}),
            ]
        )

        result = chat_service.chat(
            "hello",
            env={"OPENROUTER_API_KEYS": "plural-a,plural-b"},
            requests_client=client,
            clock=clock_from([1.0, 1.2]),
        )

        self.assertEqual(result["response"], "openrouter ok")
        self.assertEqual(result["model_used"], "openrouter/google/gemma-3-27b-it:free")
        self.assertEqual(client.calls[0]["headers"]["Authorization"], "Bearer plural-a")
        self.assertEqual(client.calls[1]["headers"]["Authorization"], "Bearer plural-b")
        self.assertNotIn("plural-a", str(result))
        self.assertNotIn("plural-b", str(result))

    def test_chat_openrouter_model_fallback_on_model_unavailable(self):
        client = FakeRequests(
            [
                FakeResponse(404, text="model not found"),
                FakeResponse(200, {"choices": [{"message": {"content": "fallback ok"}}]}),
            ]
        )

        result = chat_service.chat(
            "hello",
            env={"OPENROUTER_API_KEY": "or-secret"},
            requests_client=client,
            clock=clock_from([1.0, 1.2]),
            enable_vm_fallback=False,
        )

        self.assertEqual(result["response"], "fallback ok")
        self.assertEqual(result["model_used"], "openrouter/google/gemma-2-9b-it:free")
        self.assertEqual(client.calls[0]["json"]["model"], "google/gemma-3-27b-it:free")
        self.assertEqual(client.calls[1]["json"]["model"], "google/gemma-2-9b-it:free")
        self.assertNotIn("or-secret", str(result))

    def test_chat_does_not_model_fallback_on_invalid_openrouter_key(self):
        client = FakeRequests([FakeResponse(401, text="invalid key for or-secret")])

        result = chat_service.chat(
            "hello",
            env={"OPENROUTER_API_KEY": "or-secret"},
            requests_client=client,
            clock=clock_from([1.0, 1.2]),
            enable_vm_fallback=False,
        )

        self.assertEqual(result["model_used"], "none")
        self.assertEqual(len(client.calls), 1)
        self.assertIn("OpenRouter 401 [invalid_key]", result["errors"][0])
        self.assertNotIn("or-secret", str(result))

    def test_chat_uses_vm_fallback_after_local_failures(self):
        client = FakeRequests(
            [
                FakeResponse(401, text="gemini failed for gem-secret"),
                FakeResponse(401, text="router failed for or-secret"),
            ]
        )
        status_rows = iter(
            [
                {"online": True},
                {"online": True, "recent": []},
                {
                    "online": True,
                    "recent": [
                        {
                            "task": "[chat-fallback-fixedmarker1] hello",
                            "status": "done",
                            "result": "hello from vm",
                        }
                    ],
                },
            ]
        )
        sent_tasks = []

        def send_task(task, task_type="build", context=""):
            sent_tasks.append({"task": task, "task_type": task_type, "context": context})
            return {"ok": True, "status": "queued"}

        with patch("modules.chat_service.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "fixedmarker123"
            result = chat_service.chat(
                "hello",
                env={"GEMINI_API_KEY": "gem-secret", "OPENROUTER_API_KEY": "or-secret"},
                requests_client=client,
                clock=clock_from([1.0, 1.5]),
                vm_send_task=send_task,
                vm_get_status=lambda: next(status_rows),
                sleep_func=lambda _: None,
                vm_poll_attempts=2,
            )

        self.assertEqual(result["response"], "hello from vm")
        self.assertEqual(result["model_used"], "vm/jules-worker")
        self.assertEqual(sent_tasks[0]["task_type"], "chat")
        self.assertIn("chat-fallback-fixedmarker1", sent_tasks[0]["task"])
        self.assertNotIn("gem-secret", str(result))
        self.assertNotIn("or-secret", str(result))

    def test_chat_vm_fallback_timeout_reports_error(self):
        statuses = iter(
            [
                {"online": True},
                {"online": True, "recent": []},
                {"online": True, "recent": []},
            ]
        )

        result = chat_service.chat(
            "hello",
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.1]),
            vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
            vm_get_status=lambda: next(statuses),
            sleep_func=lambda _: None,
            vm_task_attempts=1,
            vm_poll_attempts=2,
        )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("VM fallback timed out", result["errors"][-1])

    def test_chat_vm_fallback_rejects_worker_provider_failure(self):
        statuses = iter(
            [
                {"online": True},
                {
                    "online": True,
                    "recent": [
                        {
                            "task": "[chat-fallback-fixedmarker1] hello",
                            "status": "done",
                            "result": "No LLM available - GEMINI_API_KEY is rate-limited and all OpenRouter free models failed.",
                        }
                    ],
                },
            ]
        )

        with patch("modules.chat_service.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "fixedmarker123"
            result = chat_service.chat(
                "hello",
                env={},
                requests_client=FakeRequests([]),
                clock=clock_from([1.0, 1.1]),
                vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
                vm_get_status=lambda: next(statuses),
                sleep_func=lambda _: None,
                vm_task_attempts=1,
                vm_poll_attempts=1,
            )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("VM fallback provider unavailable", result["errors"][-1])

    def test_chat_invalid_keys_reports_error(self):
        client = FakeRequests(
            [
                FakeResponse(401, text="Unauthorized"),
                FakeResponse(401, text='{"error": {"message": "Invalid API key"}}'),
            ]
        )

        result = chat_service.test_chat_providers(
            env={"GEMINI_API_KEY": "bad-gemini", "OPENROUTER_API_KEY": "bad-or"},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2, 1.3]),
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "error")
        self.assertEqual(result["providers"]["openrouter"]["status"], "error")
        self.assertEqual(result["providers"]["gemini"]["error_type"], "invalid_key")
        self.assertEqual(result["providers"]["openrouter"]["error_type"], "invalid_key")
        self.assertIn("401", result["providers"]["gemini"]["detail"])
        self.assertIn("401", result["providers"]["openrouter"]["detail"])

    def test_classify_error(self):
        self.assertEqual(chat_service._classify_error(401, "unauthorized"), "invalid_key")
        self.assertEqual(chat_service._classify_error(403, "forbidden"), "invalid_key")
        self.assertEqual(chat_service._classify_error(429, "too many requests"), "quota_limit")
        self.assertEqual(chat_service._classify_error(200, "quota hit"), "quota_limit")
        self.assertEqual(chat_service._classify_error(404, "model not found"), "model_unavailable")
        self.assertEqual(chat_service._classify_error(500, "server error"), "transient_error")
        self.assertEqual(chat_service._classify_error(400, "bad request"), "other_error")

    def test_one_provider_ok_keeps_health_true(self):
        client = FakeRequests(
            [
                FakeResponse(200),
                FakeResponse(401, text="Unauthorized"),
            ]
        )

        result = chat_service.test_chat_providers(
            env={"GEMINI_API_KEY": "good-gemini", "OPENROUTER_API_KEY": "bad-or"},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2, 1.3]),
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "ok")
        self.assertEqual(result["providers"]["openrouter"]["status"], "error")

    def test_provider_probe_keyless_mode(self):
        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["gemini"]["status"], "no_key")
        self.assertEqual(result["providers"]["openrouter"]["status"], "no_key")

    def test_openrouter_health_rotates_plural_keys_and_redacts(self):
        client = FakeRequests(
            [
                FakeResponse(401, text="bad plural-a"),
                FakeResponse(200),
            ]
        )

        result = chat_service.test_chat_providers(
            env={"OPENROUTER_API_KEYS": "plural-a,plural-b"},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2]),
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["openrouter"]["status"], "ok")
        self.assertEqual(client.calls[0]["headers"]["Authorization"], "Bearer plural-a")
        self.assertEqual(client.calls[1]["headers"]["Authorization"], "Bearer plural-b")
        self.assertNotIn("plural-a", str(result))
        self.assertNotIn("plural-b", str(result))

    def test_openrouter_health_model_fallback_on_model_unavailable(self):
        client = FakeRequests(
            [
                FakeResponse(404, text="model_not_found"),
                FakeResponse(200),
            ]
        )

        result = chat_service.test_chat_providers(
            env={"OPENROUTER_API_KEY": "or-secret"},
            requests_client=client,
            clock=clock_from([1.0, 1.1, 1.2]),
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["openrouter"]["status"], "ok")
        self.assertEqual(result["providers"]["openrouter"]["model"], "google/gemma-2-9b-it:free")
        self.assertEqual(client.calls[0]["json"]["model"], "google/gemma-3-27b-it:free")
        self.assertEqual(client.calls[1]["json"]["model"], "google/gemma-2-9b-it:free")
        self.assertNotIn("or-secret", str(result))

    def test_provider_health_reports_vm_worker_online(self):
        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_get_status=lambda: {"online": True, "tasks_completed": 3},
            probe_vm_chat=False,
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")
        self.assertEqual(result["providers"]["vm_worker"]["model"], "vm/jules-worker")

    def test_provider_health_uses_vm_send_task_in_probe_gate(self):
        with patch("modules.chat_service._vm_worker_status") as mock_status:
            mock_status.return_value = {"status": "ok", "model": "vm/jules-worker"}
            result = chat_service.test_chat_providers(
                env={},
                requests_client=FakeRequests([]),
                clock=clock_from([1.0, 1.025]),
                vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
            )

        self.assertTrue(result["healthy"])
        mock_status.assert_called_once()
        self.assertIsNotNone(mock_status.call_args.kwargs["vm_send_task"])

    def test_provider_health_rejects_recent_vm_chat_failure(self):
        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_get_status=lambda: {
                "online": True,
                "tasks_completed": 4,
                "recent": [
                    {
                        "task": "[chat-fallback-deadbeef] hello",
                        "status": "done",
                        "result": "No LLM available - GEMINI_API_KEY is rate-limited and all OpenRouter free models failed.",
                    }
                ],
            },
            probe_vm_chat=False,
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "error")
        self.assertIn("provider quota/key failure", result["providers"]["vm_worker"]["detail"])

    def test_provider_health_rejects_recent_local_vm_chat_failure(self):
        chat_service._remember_vm_chat_failure("VM fallback timed out waiting for a completed chat task")

        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_get_status=lambda: {"online": True, "tasks_completed": 4},
            probe_vm_chat=False,
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "error")
        self.assertIn("latest local chat fallback failed", result["providers"]["vm_worker"]["detail"])

    def test_provider_health_uses_recent_vm_chat_success_when_probe_times_out(self):
        chat_service._remember_vm_chat_success()

        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
            vm_get_status=lambda: {"online": True, "tasks_completed": 5, "recent": []},
            sleep_func=lambda _: None,
            vm_task_attempts=1,
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")
        self.assertIn("recently succeeded", result["providers"]["vm_worker"]["detail"])

    def test_provider_health_probe_failure_without_success_still_errors(self):
        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
            vm_get_status=lambda: {"online": True, "tasks_completed": 5, "recent": []},
            sleep_func=lambda _: None,
            vm_task_attempts=1,
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "error")
        self.assertIn("timed out", result["providers"]["vm_worker"]["detail"])

    def test_provider_health_expired_vm_chat_success_does_not_mask_failure(self):
        chat_service._LAST_VM_CHAT_SUCCESS.update(
            {"ts": chat_service.time.time() - chat_service._VM_CHAT_SUCCESS_TTL_S - 1}
        )

        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
            vm_get_status=lambda: {"online": True, "tasks_completed": 5, "recent": []},
            sleep_func=lambda _: None,
            vm_task_attempts=1,
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "error")

    def test_provider_health_dashboard_prefers_recent_success_over_local_failure(self):
        chat_service._remember_vm_chat_success()
        chat_service._remember_vm_chat_failure("VM fallback timed out waiting for a completed chat task")

        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_get_status=lambda: {"online": True, "tasks_completed": 6},
            probe_vm_chat=False,
        )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")
        self.assertIn("recently succeeded", result["providers"]["vm_worker"]["detail"])

    def test_provider_failure_clears_recent_vm_chat_success(self):
        chat_service._remember_vm_chat_success()
        chat_service._remember_vm_chat_failure(
            "VM fallback provider unavailable: worker reported no LLM available"
        )

        result = chat_service.test_chat_providers(
            env={},
            requests_client=FakeRequests([]),
            clock=clock_from([1.0, 1.025]),
            vm_get_status=lambda: {"online": True, "tasks_completed": 6},
            probe_vm_chat=False,
        )

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "error")
        self.assertIn("latest local chat fallback failed", result["providers"]["vm_worker"]["detail"])

    def test_provider_health_vm_chat_probe_success(self):
        statuses = iter(
            [
                {"online": True, "tasks_completed": 4},
                {"online": True, "tasks_completed": 4},
                {
                    "online": True,
                    "recent": [
                        {
                            "task": "[chat-fallback-fixedmarker1] Health probe",
                            "status": "done",
                            "result": "OK",
                        }
                    ],
                },
            ]
        )

        with patch("modules.chat_service.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "fixedmarker123"
            result = chat_service.test_chat_providers(
                env={},
                requests_client=FakeRequests([]),
                clock=clock_from([1.0, 1.2]),
                vm_send_task=lambda *args, **kwargs: {"ok": True, "status": "queued"},
                vm_get_status=lambda: next(statuses),
                sleep_func=lambda _: None,
            )

        self.assertTrue(result["healthy"])
        self.assertEqual(result["providers"]["vm_worker"]["status"], "ok")

    def test_sanitize_detail_redacts_plural_openrouter_keys(self):
        detail = "failed with key-a and key-b and gem-key"
        result = chat_service._sanitize_detail(
            detail,
            {"GEMINI_API_KEY": "gem-key", "OPENROUTER_API_KEYS": "key-a, key-b"},
        )

        self.assertEqual(result, "failed with [redacted] and [redacted] and [redacted]")


if __name__ == "__main__":
    unittest.main()
