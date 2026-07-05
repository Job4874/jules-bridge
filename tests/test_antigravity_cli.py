import json

import modules.antigravity_cli as antigravity_cli


def _candidate(path: str = "agy"):
    return {
        "label": "test",
        "requested": path,
        "resolved": path,
        "exists": True,
    }


def test_antigravity_preflight_writes_ready_state(monkeypatch, tmp_path):
    def fake_run(command, timeout_s, cwd=None):
        if "--version" in command:
            return {"exit_code": 0, "stdout": "1.0.16\n", "stderr": "", "timed_out": False}
        if "models" in command:
            return {"exit_code": 0, "stdout": "Gemini 3.5 Flash\n", "stderr": "", "timed_out": False}
        if "plugin" in command:
            return {"exit_code": 0, "stdout": "No imported plugins.\n", "stderr": "", "timed_out": False}
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "Available subcommands:\n  plugin    Manage plugins\n  models    List models\n",
            "timed_out": False,
        }

    state_path = tmp_path / "ANTIGRAVITY_PREFLIGHT.json"
    monkeypatch.setattr(antigravity_cli, "_candidate_antigravity_commands", lambda command: [_candidate()])
    monkeypatch.setattr(antigravity_cli, "_run_cli_command", fake_run)

    result = antigravity_cli.antigravity_preflight(state_path=str(state_path))

    assert result["ready"] is True
    assert result["installed"] is True
    assert result["version"]["stdout"] == "1.0.16\n"
    assert result["capabilities"]["subcommands"] == ["plugin", "models"]
    assert result["smoke"]["status"] == "skipped"
    assert state_path.is_file()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["ready"] is True


def test_antigravity_preflight_smoke_uses_print_mode(monkeypatch):
    monkeypatch.setattr(antigravity_cli, "_candidate_antigravity_commands", lambda command: [_candidate()])
    monkeypatch.setattr(
        antigravity_cli,
        "_run_cli_command",
        lambda command, timeout_s, cwd=None: {
            "exit_code": 0,
            "stdout": "1.0.16\n" if "--version" in command else "ok\n",
            "stderr": "Available subcommands:\n  plugin    Manage plugins\n" if "--help" in command else "",
            "timed_out": False,
        },
    )

    result = antigravity_cli.antigravity_preflight(run_smoke=True, write_state=False)

    assert result["ready"] is True
    assert result["smoke"]["status"] == "ok"
    assert "-p" in result["smoke"]["command_preview"]


def test_run_antigravity_prompt_dry_run_redacts_prompt(monkeypatch):
    monkeypatch.setattr(antigravity_cli, "_candidate_antigravity_commands", lambda command: [_candidate()])

    result = antigravity_cli.run_antigravity_prompt(
        prompt="Inspect this private source text",
        dry_run=True,
        write_state=False,
    )

    assert result["status"] == "dry_run"
    assert "[prompt:32 chars]" in result["command_preview"]
    assert "Inspect this private source text" not in result["command_preview"]


def test_run_antigravity_prompt_live_builds_headless_command(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, timeout_s, cwd=None):
        calls.append((command, timeout_s, cwd))
        return {"exit_code": 0, "stdout": "done\n", "stderr": "", "timed_out": False}

    monkeypatch.setattr(antigravity_cli, "_candidate_antigravity_commands", lambda command: [_candidate()])
    monkeypatch.setattr(antigravity_cli, "_run_cli_command", fake_run)
    state_path = tmp_path / "prompt.json"

    result = antigravity_cli.run_antigravity_prompt(
        prompt="Say done",
        cwd=str(tmp_path),
        model="Gemini 3.5 Flash (High)",
        dry_run=False,
        state_path=str(state_path),
    )

    assert result["status"] == "ok"
    command = calls[0][0]
    assert "-p" in command
    assert "Say done" in command
    assert "--print-timeout" in command
    assert "--model" in command
    assert "Gemini 3.5 Flash (High)" in command
    assert calls[0][2] == str(tmp_path)
    assert state_path.is_file()


def test_antigravity_status_snapshot_reads_preflight_state(monkeypatch, tmp_path):
    state_path = tmp_path / "ANTIGRAVITY_PREFLIGHT.json"
    state_path.write_text(
        json.dumps({
            "ready": True,
            "likely_blocker": "",
            "version": {"stdout": "1.0.16\n"},
            "capabilities": {"models": {"stdout": "Gemini 3.5 Flash\nClaude Sonnet\n"}},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(antigravity_cli, "_candidate_antigravity_commands", lambda command: [_candidate()])

    result = antigravity_cli.antigravity_status_snapshot(state_path=str(state_path))

    assert result["installed"] is True
    assert result["ready"] is True
    assert result["version"] == "1.0.16"
    assert result["model_count"] == 2
    assert result["state_path"] == str(state_path)
