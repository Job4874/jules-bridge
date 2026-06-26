import pytest
from unittest.mock import patch, MagicMock

from modules.vm_manager import boot_secondary_vm, VMBootError, get_local_memory_percent


class TestGetLocalMemoryPercent:
    @patch("psutil.virtual_memory")
    def test_returns_virtual_memory_percent(self, mock_virtual_memory):
        mock_virtual_memory.return_value.percent = 42.0
        assert get_local_memory_percent() == 42.0


class TestBootSecondaryVM:
    @patch("psutil.virtual_memory")
    def test_no_action_when_memory_low(self, mock_virtual_memory):
        mock_virtual_memory.return_value.percent = 50.0
        result = boot_secondary_vm()
        assert result["status"] == "no_action"
        assert result["memory_percent"] == 50.0

    @patch("psutil.virtual_memory")
    def test_dry_run_when_memory_high(self, mock_virtual_memory):
        mock_virtual_memory.return_value.percent = 90.0
        result = boot_secondary_vm(dry_run=True)
        assert result["status"] == "dry_run"
        assert "az vm start" in result["message"]

    @patch("psutil.virtual_memory")
    def test_blocks_live_boot_without_allow_flag(self, mock_virtual_memory):
        mock_virtual_memory.return_value.percent = 90.0
        with pytest.raises(VMBootError):
            boot_secondary_vm(dry_run=False, allow_vm_boot=False)

    @patch("modules.vm_manager.subprocess.run")
    @patch("psutil.virtual_memory")
    def test_executes_live_boot_when_allowed(self, mock_virtual_memory, mock_run):
        mock_virtual_memory.return_value.percent = 90.0
        mock_run.return_value = MagicMock(returncode=0)
        result = boot_secondary_vm(dry_run=False, allow_vm_boot=True)
        assert result["status"] == "executed"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:4] == ["az", "vm", "start", "--name"]

    @patch("modules.vm_manager.subprocess.run")
    @patch("psutil.virtual_memory")
    def test_returns_failed_on_azure_error(self, mock_virtual_memory, mock_run):
        mock_virtual_memory.return_value.percent = 90.0
        import subprocess as sp
        mock_run.side_effect = sp.CalledProcessError(1, "az", stderr="boom")
        result = boot_secondary_vm(dry_run=False, allow_vm_boot=True)
        assert result["status"] == "failed"
        assert result.get("stderr") == "boom"

    @patch("modules.vm_manager.subprocess.run")
    @patch("psutil.virtual_memory")
    def test_returns_failed_when_azure_cli_missing(
        self, mock_virtual_memory, mock_run
    ):
        mock_virtual_memory.return_value.percent = 90.0
        mock_run.side_effect = FileNotFoundError("az not found")
        result = boot_secondary_vm(dry_run=False, allow_vm_boot=True)
        assert result["status"] == "failed"
        assert "Azure CLI not found" in result["error"]
