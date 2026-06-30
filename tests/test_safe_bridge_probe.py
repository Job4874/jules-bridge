import unittest

from self_created_tools import safe_bridge_probe


class TestSafeBridgeProbe(unittest.TestCase):
    def test_sanitize_omits_image_and_redacts_sensitive_fields(self):
        result = safe_bridge_probe.sanitize(
            {
                "image_base64": "abc123",
                "Authorization": "Bearer token",
                "nested": {"api_key": "secret", "ok": "value"},
            }
        )

        self.assertEqual(result["image_base64"], safe_bridge_probe.OMITTED_IMAGE)
        self.assertEqual(result["Authorization"], "<redacted>")
        self.assertEqual(result["nested"]["api_key"], "<redacted>")
        self.assertEqual(result["nested"]["ok"], "value")

    def test_summarize_oracle_status_keeps_gate_fields_without_account_identity(self):
        result = safe_bridge_probe.summarize_oracle_status(
            {
                "blockers": [],
                "branch": "main",
                "quantower": {"running": True},
                "instance": {
                    "exists": True,
                    "instance_id": "abc",
                    "state": "50",
                    "primary_symbol_label": "MES",
                    "symbol_bound": True,
                    "account_bound": "DEMO-123",
                    "account": "SHOULD_NOT_LEAK",
                    "enable_live_trading": "false",
                    "enable_dry_run_mode": "false",
                },
                "gates": {"g3_dry_run_proof": False},
                "telemetry": {
                    "file": "heartbeat.csv",
                    "last_write_utc": "2026-06-28T00:00:00Z",
                    "pipeline_active": True,
                },
                "verify": {"code": 1, "checks": [{"ok": False}]},
                "next_actions": ["grep"],
            }
        )

        self.assertTrue(result["account_bound"])
        self.assertNotIn("account", result)
        self.assertEqual(result["gates"]["g3_dry_run_proof"], False)
        self.assertEqual(result["verify_code"], 1)

    def test_screenshot_summary_never_returns_raw_base64(self):
        result = safe_bridge_probe.summarize(
            "screenshot",
            "/ui/screenshot?save=true",
            {"saved_path": "screen.png", "image_base64": "abc123"},
        )

        self.assertEqual(result["saved_path"], "screen.png")
        self.assertEqual(result["image_base64"], safe_bridge_probe.OMITTED_IMAGE)

    def test_build_url_normalizes_slashes(self):
        self.assertEqual(
            safe_bridge_probe.build_url("ping", "https://example.test/"),
            "https://example.test/ping",
        )


if __name__ == "__main__":
    unittest.main()
