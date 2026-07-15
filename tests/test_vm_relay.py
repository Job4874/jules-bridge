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
        mock_env.return_value = {"BROWSER_MODEL_LOOP_URL": "http://127.0.0.1:8765/model-loop"}
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
        mock_env.return_value = {"BROWSER_MODEL_LOOP_URL": "http://127.0.0.1:8765/model-loop"}
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


def test_worker_agent_script_uses_browser_model_loop_only():
    from modules.vm_relay import _build_worker_agent_script  # pylint: disable=import-outside-toplevel

    script = _build_worker_agent_script()

    assert "BROWSER_MODEL_LOOP_URL" in script
    assert "generativelanguage.googleapis.com" not in script
    assert "openrouter.ai" not in script
    assert "GEMINI_API_KEY" not in script
    assert "OPENROUTER_API_KEY" not in script


def test_worker_env_uses_configured_bridge_token_without_provider_keys():
    from modules.vm_relay import _build_worker_env  # pylint: disable=import-outside-toplevel

    env_text = _build_worker_env(
        {
            "BROWSER_MODEL_LOOP_URL": "http://10.0.0.5:8765/model-loop",
            "BRIDGE_TOKEN": "configured-token",
        },
        "10.0.0.2",
    )

    assert "BROWSER_MODEL_LOOP_URL=http://10.0.0.5:8765/model-loop" in env_text
    assert "LOCAL_BRIDGE_URL=http://10.0.0.2:5000" in env_text
    assert "LOCAL_BRIDGE_TOKEN=configured-token" in env_text
    assert "GEMINI_API_KEY" not in env_text
    assert "OPENROUTER_API_KEY" not in env_text
