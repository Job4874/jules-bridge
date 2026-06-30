"""TDD tests for modules/vm_relay.py."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

class TestBootstrapVM:
    @patch("modules.vm_relay._log")
    @patch("modules.vm_relay._gcloud_ssh")
    @patch("modules.vm_relay._gcloud_scp")
    @patch("modules.vm_relay._build_worker_agent_script")
    @patch("modules.vm_relay._env")
    @patch("modules.vm_relay._get_local_ip")
    def test_bootstrap_vm_success(
        self,
        mock_get_local_ip,
        mock_env,
        mock_build_script,
        mock_scp,
        mock_ssh,
        mock_log,
    ):
        mock_ssh.return_value = ("stdout", "stderr", 0)
        mock_scp.return_value = ("stdout", "stderr", 0)
        mock_build_script.return_value = "dummy script"
        mock_env.return_value = {"GEMINI_API_KEY": "test", "OPENROUTER_API_KEY": "test"}
        mock_get_local_ip.return_value = "127.0.0.1"

        from modules.vm_relay import bootstrap_vm  # pylint: disable=import-outside-toplevel

        result = bootstrap_vm()

        assert result["ok"] is True
        assert result["vm"] is not None
        assert len(result["steps"]) == 4
        for step in result["steps"]:
            assert step["rc"] == 0

    @patch("modules.vm_relay._log")
    @patch("modules.vm_relay._gcloud_ssh")
    @patch("modules.vm_relay._gcloud_scp")
    @patch("modules.vm_relay._build_worker_agent_script")
    @patch("modules.vm_relay._env")
    @patch("modules.vm_relay._get_local_ip")
    def test_bootstrap_vm_failure_on_first_step(
        self,
        mock_get_local_ip,
        mock_env,
        mock_build_script,
        mock_scp,
        mock_ssh,
        mock_log,
    ):
        # First ssh call (install deps) fails with rc 1
        # Subsequent ssh and scp calls return rc 0
        mock_ssh.side_effect = [("stdout", "error", 1), ("stdout", "stderr", 0)]
        mock_scp.return_value = ("stdout", "stderr", 0)
        mock_build_script.return_value = "dummy script"
        mock_env.return_value = {"GEMINI_API_KEY": "test", "OPENROUTER_API_KEY": "test"}
        mock_get_local_ip.return_value = "127.0.0.1"

        from modules.vm_relay import bootstrap_vm  # pylint: disable=import-outside-toplevel

        result = bootstrap_vm()

        assert result["ok"] is False
        assert result["vm"] is not None
        assert len(result["steps"]) == 4
        assert result["steps"][0]["rc"] == 1
        assert result["steps"][1]["rc"] == 0
        assert result["steps"][2]["rc"] == 0
        assert result["steps"][3]["rc"] == 0
