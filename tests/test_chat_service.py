"""Tests for chat provider routing."""

import unittest

from modules import chat_service


class FakeRequests:
    def __init__(self, is_vm_test=False):
        self._is_vm_test = is_vm_test


def clock_from(values):
    iterator = iter(values)
    return lambda: next(iterator)


class TestChatProviderHealth(unittest.TestCase):
    def test_vm_offline(self):
        result = chat_service.test_chat_providers(env={}, requests_client=FakeRequests())

        self.assertFalse(result["healthy"])
        self.assertEqual(result["providers"]["vm"]["status"], "offline")


class TestChatCompletion(unittest.TestCase):
    def test_chat_offline_response_is_stable(self):
        result = chat_service.chat(
            "hello",
            env={},
            requests_client=FakeRequests(),
            clock=clock_from([1.0, 1.0]),
        )

        self.assertEqual(result["model_used"], "none")
        self.assertIn("offline", result["response"])
        self.assertIn("VM relay requires requests module (no overrides)", result["errors"])


if __name__ == "__main__":
    unittest.main()
