import json
from pathlib import Path

import modules.gemini_cli as gemini_cli


def _candidate(path: str = "gemini"):
    return {
        "label": "requested",
        "requested": path,
        "resolved": path,
        "exists": True,
    }


def test_gemini_preflight_writes_ready_state(monkeypatch, tmp_path):
    def fake_run(command, timeout_s, cwd=None):
        if "--version" in command:
            return {"exit_code": 0, "stdout": "0.49.0\n", "stderr": "", "timed_out": False}
        return {"exit_code": 0, "stdout": "ok\n", "stderr": "", "timed_out": False}

    state_path = tmp_path / "GEMINI_PREFLIGHT.json"
    monkeypatch.setattr(gemini_cli, "_candidate_gemini_commands", lambda command: [_candidate()])
    monkeypatch.setattr(gemini_cli, "_run_cli_command", fake_run)

    result = gemini_cli.gemini_preflight(state_path=str(state_path))

    assert result["ready"] is True
    assert result["installed"] is True
    assert result["version"]["stdout"] == "0.49.0\n"
    assert result["smoke"]["status"] == "skipped"
    assert state_path.is_file()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["ready"] is True


def test_gemini_preflight_smoke_uses_plan_mode(monkeypatch):
    monkeypatch.setattr(gemini_cli, "_candidate_gemini_commands", lambda command: [_candidate()])
    monkeypatch.setattr(
        gemini_cli,
        "_run_cli_command",
        lambda command, timeout_s, cwd=None: {
            "exit_code": 0,
            "stdout": "0.49.0\n" if "--version" in command else "ok\n",
            "stderr": "",
            "timed_out": False,
        },
    )

    result = gemini_cli.gemini_preflight(run_smoke=True, write_state=False)

    assert result["ready"] is True
    assert result["smoke"]["status"] == "ok"
    assert result["smoke"]["approval_mode"] == "plan"


def test_run_gemini_prompt_dry_run_redacts_prompt(monkeypatch):
    monkeypatch.setattr(gemini_cli, "_candidate_gemini_commands", lambda command: [_candidate()])

    result = gemini_cli.run_gemini_prompt(
        prompt="Inspect this private source text",
        dry_run=True,
        write_state=False,
    )

    assert result["status"] == "dry_run"
    assert result["approval_mode"] == "plan"
    assert "[prompt:32 chars]" in result["command_preview"]
    assert "Inspect this private source text" not in result["command_preview"]


def test_run_gemini_prompt_live_builds_headless_command(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, timeout_s, cwd=None):
        calls.append((command, timeout_s, cwd))
        return {"exit_code": 0, "stdout": "done\n", "stderr": "", "timed_out": False}

    monkeypatch.setattr(gemini_cli, "_candidate_gemini_commands", lambda command: [_candidate()])
    monkeypatch.setattr(gemini_cli, "_run_cli_command", fake_run)
    state_path = tmp_path / "prompt.json"

    result = gemini_cli.run_gemini_prompt(
        prompt="Say done",
        cwd=str(tmp_path),
        model="gemini-3-pro",
        dry_run=False,
        state_path=str(state_path),
    )

    assert result["status"] == "ok"
    command = calls[0][0]
    assert "-p" in command
    assert "Say done" in command
    assert "--approval-mode" in command
    assert "plan" in command
    assert "--model" in command
    assert "gemini-3-pro" in command
    assert "--skip-trust" in command
    assert calls[0][2] == str(tmp_path)
    assert state_path.is_file()


def test_gemini_status_snapshot_reads_preflight_state(monkeypatch, tmp_path):
    state_path = tmp_path / "GEMINI_PREFLIGHT.json"
    state_path.write_text(
        json.dumps({
            "ready": True,
            "likely_blocker": "",
            "version": {"stdout": "0.49.0\n"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(gemini_cli, "_candidate_gemini_commands", lambda command: [_candidate()])

    result = gemini_cli.gemini_status_snapshot(state_path=str(state_path))

    assert result["installed"] is True
    assert result["ready"] is True
    assert result["version"] == "0.49.0"
    assert result["state_path"] == str(state_path)
