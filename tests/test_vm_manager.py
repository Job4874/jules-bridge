"""TDD tests for modules/vm_manager.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestResourcePressure:
    def test_detect_resource_pressure_reports_ok_for_injected_safe_metrics(self):
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure(
            cpu_percent=42,
            memory_percent=61,
            thresholds={"cpu_percent": 80, "memory_percent": 90},
        )

        assert result["status"] == "ok"
        assert result["cpu_percent"] == 42.0
        assert result["memory_percent"] == 61.0
        assert result["maxed_out"] is False
        assert result["reasons"] == []
        assert result["error"] is None

    def test_detect_resource_pressure_flags_cpu_and_memory_thresholds(self):
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure(
            cpu_percent=91,
            memory_percent=96,
            thresholds={"cpu_percent": 90, "memory_percent": 95},
        )

        assert result["status"] == "maxed_out"
        assert result["maxed_out"] is True
        assert any(reason.startswith("cpu_percent") for reason in result["reasons"])
        assert any(reason.startswith("memory_percent") for reason in result["reasons"])
        assert result["error"] is None

    def test_detect_resource_pressure_rejects_negative_metrics(self):
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure(cpu_percent=-1, memory_percent=50)

        assert result["status"] == "error"
        assert result["maxed_out"] is False
        assert "0 and 100" in result["error"]

    @patch("modules.vm_manager._read_host_metrics")
    def test_detect_resource_pressure_reads_host_metrics_when_omitted(self, mock_read_host_metrics):
        mock_read_host_metrics.return_value = (55.0, 75.0, None)
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure(thresholds={"cpu_percent": 80, "memory_percent": 90})

        assert result["status"] == "ok"
        assert result["cpu_percent"] == 55.0
        assert result["memory_percent"] == 75.0
        assert result["maxed_out"] is False
        assert result["error"] is None

    @patch("modules.vm_manager._read_host_metrics")
    def test_detect_resource_pressure_handles_host_metric_error(self, mock_read_host_metrics):
        mock_read_host_metrics.return_value = (None, None, "host metric reader failed")
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure()

        assert result["status"] == "error"
        assert result["cpu_percent"] is None
        assert result["memory_percent"] is None
        assert result["maxed_out"] is False
        assert result["error"] == "host metric reader failed"

    @patch("modules.vm_manager._read_host_metrics")
    def test_detect_resource_pressure_catches_unexpected_exceptions(self, mock_read_host_metrics):
        mock_read_host_metrics.side_effect = Exception("unexpected error")
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        result = detect_resource_pressure()

        assert result["status"] == "error"
        assert result["cpu_percent"] is None
        assert result["memory_percent"] is None
        assert result["maxed_out"] is False
        assert result["error"] == "unexpected error"


class TestBootSecondaryVM:
    def test_boot_secondary_vm_defaults_to_dry_run_for_allowlisted_script(
        self,
        tmp_path,
        monkeypatch,
    ):
        script = tmp_path / "Start-SecondaryVM.ps1"
        script.write_text("Write-Output 'start'", encoding="utf-8")
        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))

        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        result = boot_secondary_vm("Start-SecondaryVM.ps1")

        assert result["status"] == "dry_run"
        assert result["selected_script"] == str(script)
        assert result["started"] is False
        assert result["dry_run"] is True
        assert result["error"] is None

    def test_boot_secondary_vm_blocks_real_start_without_allow_flag(
        self,
        tmp_path,
        monkeypatch,
    ):
        script = tmp_path / "Start-SecondaryVM.ps1"
        script.write_text("Write-Output 'start'", encoding="utf-8")
        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))

        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        result = boot_secondary_vm(
            "Start-SecondaryVM.ps1",
            allow_vm_boot=False,
            dry_run=False,
        )

        assert result["status"] == "blocked"
        assert result["selected_script"] == str(script)
        assert result["started"] is False
        assert result["dry_run"] is False
        assert "allow_vm_boot" in result["error"]

    def test_boot_secondary_vm_rejects_path_traversal(self, monkeypatch, tmp_path):
        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))

        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        result = boot_secondary_vm(r"..\Start-SecondaryVM.ps1")

        assert result["status"] == "error"
        assert result["selected_script"] == ""
        assert result["started"] is False
        assert "simple file name" in result["error"]

    @patch("modules.vm_manager.subprocess.Popen")
    def test_boot_secondary_vm_starts_allowlisted_script_when_explicitly_allowed(
        self,
        mock_popen,
        tmp_path,
        monkeypatch,
    ):
        script = tmp_path / "Start-SecondaryVM.ps1"
        script.write_text("Write-Output 'start'", encoding="utf-8")
        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))
        mock_popen.return_value = MagicMock(pid=4242)

        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        result = boot_secondary_vm(
            "Start-SecondaryVM.ps1",
            allow_vm_boot=True,
            dry_run=False,
        )

        assert result["status"] == "started"
        assert result["selected_script"] == str(script)
        assert result["started"] is True
        assert result["dry_run"] is False
        assert result["pid"] == 4242
        assert result["error"] is None
        assert mock_popen.call_args.args[0][:4] == [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
        ]

class TestInternalHelpers:
    def test_as_percent(self):
        from modules.vm_manager import _as_percent  # pylint: disable=import-outside-toplevel
        import pytest

        assert _as_percent(None, "test") is None
        assert _as_percent(50, "test") == 50.0
        assert _as_percent("42.5", "test") == 42.5

        with pytest.raises(ValueError, match="test must be a number between 0 and 100"):
            _as_percent("invalid", "test")

        with pytest.raises(ValueError, match="test must be a number between 0 and 100"):
            _as_percent(-1, "test")

        with pytest.raises(ValueError, match="test must be a number between 0 and 100"):
            _as_percent(101, "test")

    def test_threshold_value(self):
        from modules.vm_manager import _threshold_value  # pylint: disable=import-outside-toplevel

        # Test missing dict
        assert _threshold_value(None, "cpu", 90.0) == 90.0

        # Test missing key
        assert _threshold_value({"mem": 80}, "cpu", 90.0) == 90.0

        # Test valid value
        assert _threshold_value({"cpu": 75}, "cpu", 90.0) == 75.0

        # Test None value falls back to default
        assert _threshold_value({"cpu": None}, "cpu", 90.0) == 90.0

class TestReadHostMetrics:
    @patch("modules.vm_manager.subprocess.run")
    def test_read_host_metrics_success(self, mock_run):
        from modules.vm_manager import _read_host_metrics  # pylint: disable=import-outside-toplevel
        import json

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"cpu_percent": 45.5, "memory_percent": 60.2})
        mock_run.return_value = mock_result

        cpu, mem, err = _read_host_metrics()

        assert cpu == 45.5
        assert mem == 60.2
        assert err is None

    @patch("modules.vm_manager.subprocess.run")
    def test_read_host_metrics_non_zero_exit(self, mock_run):
        from modules.vm_manager import _read_host_metrics  # pylint: disable=import-outside-toplevel

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        cpu, mem, err = _read_host_metrics()

        assert cpu is None
        assert mem is None
        assert err == "host metric reader failed"

    @patch("modules.vm_manager.subprocess.run")
    def test_read_host_metrics_exception(self, mock_run):
        from modules.vm_manager import _read_host_metrics  # pylint: disable=import-outside-toplevel
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell.exe", timeout=10)

        cpu, mem, err = _read_host_metrics()

        assert cpu is None
        assert mem is None
        assert err == "host metric reader failed"

    @patch("modules.vm_manager._read_host_metrics")
    def test_detect_resource_pressure_uses_host_metrics_fallback(self, mock_read):
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        mock_read.return_value = (50.0, 70.0, None)

        result = detect_resource_pressure()

        assert result["cpu_percent"] == 50.0
        assert result["memory_percent"] == 70.0
        assert result["status"] == "ok"

    @patch("modules.vm_manager._read_host_metrics")
    def test_detect_resource_pressure_host_metrics_failure(self, mock_read):
        from modules.vm_manager import detect_resource_pressure  # pylint: disable=import-outside-toplevel

        mock_read.return_value = (None, None, "host metric reader failed")

        result = detect_resource_pressure()

        assert result["status"] == "error"
        assert result["error"] == "host metric reader failed"

class TestScriptResolution:
    def test_resolve_script_empty_name(self):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        result = boot_secondary_vm("")
        assert result["status"] == "error"
        assert "script_name is required" in result["error"]

    def test_resolve_script_missing_env(self, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        monkeypatch.delenv("JULES_VM_SCRIPT_DIR", raising=False)
        result = boot_secondary_vm("script.ps1")
        assert result["status"] == "error"
        assert "JULES_VM_SCRIPT_DIR is required" in result["error"]

    def test_resolve_script_non_existent_dir(self, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", "/does/not/exist/dir/123")
        result = boot_secondary_vm("script.ps1")
        assert result["status"] == "error"
        assert "must point to an existing directory" in result["error"]

    def test_resolve_script_invalid_extension(self, tmp_path, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))
        result = boot_secondary_vm("script.txt")
        assert result["status"] == "error"
        assert "must end with one of" in result["error"]

    def test_resolve_script_file_not_found(self, tmp_path, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))
        result = boot_secondary_vm("missing.ps1")
        assert result["status"] == "error"
        assert "selected VM script was not found" in result["error"]


    @patch("modules.vm_manager.subprocess.Popen")
    def test_boot_secondary_vm_cmd_script(self, mock_popen, tmp_path, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel

        script = tmp_path / "start.cmd"
        script.write_text("echo start", encoding="utf-8")
        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))
        mock_popen.return_value = MagicMock(pid=9999)

        result = boot_secondary_vm(
            "start.cmd",
            allow_vm_boot=True,
            dry_run=False,
        )

        assert result["status"] == "started"
        assert result["pid"] == 9999
        assert mock_popen.call_args.args[0][:3] == ["cmd.exe", "/d", "/c"]


    def test_resolve_script_relative_to_raises(self, tmp_path, monkeypatch):
        from modules.vm_manager import boot_secondary_vm  # pylint: disable=import-outside-toplevel
        from pathlib import Path

        monkeypatch.setenv("JULES_VM_SCRIPT_DIR", str(tmp_path))

        # To hit the ValueError in relative_to, we mock Path.relative_to
        with patch.object(Path, 'relative_to', side_effect=ValueError("Test error")):
            result = boot_secondary_vm("script.ps1")

        assert result["status"] == "error"
        assert "must resolve inside the VM script directory" in result["error"]

    def test_threshold_value_invalid_string(self):
        from modules.vm_manager import _threshold_value  # pylint: disable=import-outside-toplevel

        # When value cannot be parsed to float, it returns None from _as_percent which raises ValueError,
        # but _as_percent actually raises ValueError. Let's make sure it raises or handled
        import pytest
        with pytest.raises(ValueError, match="cpu must be a number"):
            _threshold_value({"cpu": "invalid"}, "cpu", 90.0)

    def test_threshold_value_returns_default_when_as_percent_returns_none(self):
        from modules.vm_manager import _threshold_value  # pylint: disable=import-outside-toplevel

        # Test where value is valid but somehow None (e.g. if _as_percent could return None for non-None input,
        # but _as_percent only returns None if input is None, which is handled earlier.
        # To get 100% on line 81, we mock _as_percent to return None.
        with patch("modules.vm_manager._as_percent", return_value=None):
            assert _threshold_value({"cpu": 75}, "cpu", 90.0) == 90.0

class TestCheckAndScaleCompute:
    @patch("modules.vm_manager.detect_resource_pressure")
    @patch("modules.vm_manager.boot_secondary_vm")
    def test_check_and_scale_compute_maxed_out(self, mock_boot, mock_detect):
        from modules.vm_manager import check_and_scale_compute  # pylint: disable=import-outside-toplevel
        mock_detect.return_value = {"maxed_out": True, "memory_percent": 95.0, "status": "maxed_out"}
        mock_boot.return_value = {"status": "started"}

        result = check_and_scale_compute(dry_run=False, allow_vm_boot=True)

        assert "EXECUTED: az vm start --name OracleV5" in result
        assert "(status: started)" in result
        mock_boot.assert_called_once_with("Start-SecondaryVM.ps1", allow_vm_boot=True, dry_run=False)

    @patch("modules.vm_manager.detect_resource_pressure")
    @patch("modules.vm_manager.boot_secondary_vm")
    def test_check_and_scale_compute_no_action(self, mock_boot, mock_detect):
        from modules.vm_manager import check_and_scale_compute  # pylint: disable=import-outside-toplevel
        mock_detect.return_value = {"maxed_out": False, "memory_percent": 50.0, "status": "ok"}

        result = check_and_scale_compute()

        assert "Memory at 50.0%, no action needed." in result
        mock_boot.assert_not_called()
