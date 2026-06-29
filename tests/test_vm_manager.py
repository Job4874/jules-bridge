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
