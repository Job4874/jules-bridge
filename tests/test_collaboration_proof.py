import json

import modules.collaboration_proof as proof


def _jules_ready():
    return {
        "ready": True,
        "rest_api": True,
        "preferred_jules_command": "JULES_REST_API",
        "resolved_jules_command": "JULES_REST_API",
        "auth_indicators": {"source": "sources/github/Job4874/jules-bridge"},
        "remote": {"status": "ok"},
    }


def _gemini_ready(smoke_status="ok"):
    ready = smoke_status == "ok"
    return {
        "ready": ready,
        "installed": True,
        "likely_blocker": "" if ready else "auth_required",
        "resolved_gemini_command": "node bundle/gemini.js",
        "version": {"stdout": "0.49.0\n"},
        "capabilities": {
            "headless_mode": "-p/--prompt",
            "output_formats": ["json", "stream-json", "text"],
            "skills": {
                "stdout": (
                    "Discovered Agent Skills:\n\n"
                    "skill-creator [Enabled] [Built-in]\n"
                    "  Description: Guide for creating effective skills.\n"
                    "  Location: C:\\gemini\\skill-creator\\SKILL.md\n"
                )
            },
        },
        "smoke": {
            "status": smoke_status,
            "exit_code": 0 if ready else 1,
            "likely_blocker": "" if ready else "auth_required",
        },
    }


def _antigravity_ready(smoke_status="ok"):
    ready = smoke_status == "ok"
    return {
        "ready": ready,
        "installed": True,
        "likely_blocker": "" if ready else "auth_required",
        "resolved_antigravity_command": r"C:\Users\abdul\AppData\Local\agy\bin\agy.exe",
        "version": {"stdout": "1.0.16\n"},
        "capabilities": {
            "headless_mode": "-p/--print",
            "plugin_management": "plugin list/install/uninstall/enable/disable",
            "subcommands": ["changelog", "install", "models", "plugin", "update"],
            "models": {"stdout": "Gemini 3.5 Flash\nClaude Sonnet 4.6\n"},
            "plugin_list": {"stdout": "No imported plugins.\n"},
        },
        "smoke": {
            "status": smoke_status,
            "exit_code": 0 if ready else 1,
            "likely_blocker": "" if ready else "auth_required",
        },
    }


def _akc_ready():
    return {
        "ready": True,
        "status": "ready",
        "present_rules": ["context_system", "hrm_reasoning", "evidence_gates"],
    }


def _test_evidence():
    return {
        "passed": True,
        "test_count": 451,
        "timestamp_utc": "2026-07-05T14:55:57+00:00",
        "output_hash": "abc123",
        "raw_output_tail": "451 passed in 18.78s",
    }


def _jules_skills():
    return [
        {"name": "architect", "description": "Plan changes"},
        {"name": "imprint", "description": "Capture patterns"},
        {"name": "review", "description": "Review changes"},
        {"name": "recover", "description": "Recover from loops"},
        {"name": "remember", "description": "Write memory"},
    ]


def test_collaboration_proof_passes_when_all_required_gates_are_ready(monkeypatch):
    monkeypatch.setattr(proof, "jules_preflight", lambda **kwargs: _jules_ready())
    monkeypatch.setattr(proof, "gemini_preflight", lambda **kwargs: _gemini_ready())
    monkeypatch.setattr(proof, "antigravity_preflight", lambda **kwargs: _antigravity_ready())
    monkeypatch.setattr(proof, "check_akc_readiness", lambda: _akc_ready())
    monkeypatch.setattr(proof, "_latest_test_evidence", _test_evidence)
    monkeypatch.setattr(proof, "_jules_skill_inventory", _jules_skills)

    result = proof.build_collaboration_proof(
        include_live_checks=True,
        run_gemini_smoke=True,
        write_state=False,
    )

    assert result["status"] == "pass"
    assert result["proof_policy"]["jules_sessions_created"] is False
    assert result["proof_policy"]["gemini_live_edits"] is False
    assert result["agents"]["jules"]["skill_count"] == 5
    assert result["agents"]["gemini"]["skill_count"] == 1
    assert result["agents"]["antigravity"]["skill_count"] == 3
    assert result["completion_assessment"]["safe_to_mark_goal_complete"] is True
    assert all(row["status"] == "pass" for row in result["requirement_audit"])


def test_collaboration_proof_treats_legacy_gemini_auth_as_caveat_when_antigravity_passes(monkeypatch):
    monkeypatch.setattr(proof, "jules_preflight", lambda **kwargs: _jules_ready())
    monkeypatch.setattr(proof, "gemini_preflight", lambda **kwargs: _gemini_ready("failed"))
    monkeypatch.setattr(proof, "antigravity_preflight", lambda **kwargs: _antigravity_ready())
    monkeypatch.setattr(proof, "check_akc_readiness", lambda: _akc_ready())
    monkeypatch.setattr(proof, "_latest_test_evidence", _test_evidence)
    monkeypatch.setattr(proof, "_jules_skill_inventory", _jules_skills)

    result = proof.build_collaboration_proof(
        run_gemini_smoke=True,
        write_state=False,
    )

    assert result["status"] == "pass"
    assert result["blockers"] == []
    assert any(item["gate"] == "gemini_model_execution" for item in result["legacy_caveats"])
    gemini_gate = next(gate for gate in result["gates"] if gate["name"] == "gemini_model_execution")
    assert gemini_gate["blocker"] == "auth_required"
    assert gemini_gate["required"] is False
    google_gate = next(gate for gate in result["gates"] if gate["name"] == "google_terminal_model_execution")
    assert google_gate["status"] == "pass"
    legacy_req = next(row for row in result["requirement_audit"] if row["id"] == "REQ-003")
    assert legacy_req["status"] == "blocked"
    assert legacy_req["required_for_completion"] is False
    end_to_end = next(row for row in result["requirement_audit"] if row["id"] == "REQ-009")
    assert end_to_end["status"] == "pass"
    assert result["completion_assessment"]["safe_to_mark_goal_complete"] is True


def test_collaboration_proof_blocks_when_supported_google_terminal_smoke_fails(monkeypatch):
    monkeypatch.setattr(proof, "jules_preflight", lambda **kwargs: _jules_ready())
    monkeypatch.setattr(proof, "gemini_preflight", lambda **kwargs: _gemini_ready("failed"))
    monkeypatch.setattr(proof, "antigravity_preflight", lambda **kwargs: _antigravity_ready("failed"))
    monkeypatch.setattr(proof, "check_akc_readiness", lambda: _akc_ready())
    monkeypatch.setattr(proof, "_latest_test_evidence", _test_evidence)
    monkeypatch.setattr(proof, "_jules_skill_inventory", _jules_skills)

    result = proof.build_collaboration_proof(
        run_gemini_smoke=True,
        write_state=False,
    )

    assert result["status"] == "blocked"
    assert any(item["gate"] == "google_terminal_model_execution" for item in result["blockers"])
    assert result["completion_assessment"]["safe_to_mark_goal_complete"] is False


def test_collaboration_proof_default_keeps_gemini_smoke_skipped(monkeypatch):
    monkeypatch.setattr(proof, "jules_preflight", lambda **kwargs: _jules_ready())
    monkeypatch.setattr(proof, "gemini_preflight", lambda **kwargs: _gemini_ready())
    monkeypatch.setattr(proof, "antigravity_preflight", lambda **kwargs: _antigravity_ready())
    monkeypatch.setattr(proof, "check_akc_readiness", lambda: _akc_ready())
    monkeypatch.setattr(proof, "_latest_test_evidence", _test_evidence)
    monkeypatch.setattr(proof, "_jules_skill_inventory", _jules_skills)

    result = proof.build_collaboration_proof(write_state=False)

    gemini_gate = next(gate for gate in result["gates"] if gate["name"] == "gemini_model_execution")
    assert gemini_gate["status"] == "skipped"
    google_gate = next(gate for gate in result["gates"] if gate["name"] == "google_terminal_model_execution")
    assert google_gate["status"] == "skipped"
    assert result["proof_policy"]["gemini_smoke_requested"] is False
    assert result["proof_policy"]["antigravity_smoke_requested"] is False
    assert any(gate["name"] == "actual_code_changes" for gate in result["gates"])


def test_collaboration_proof_state_file_includes_state_path(monkeypatch, tmp_path):
    monkeypatch.setattr(proof, "jules_preflight", lambda **kwargs: _jules_ready())
    monkeypatch.setattr(proof, "gemini_preflight", lambda **kwargs: _gemini_ready())
    monkeypatch.setattr(proof, "antigravity_preflight", lambda **kwargs: _antigravity_ready())
    monkeypatch.setattr(proof, "check_akc_readiness", lambda: _akc_ready())
    monkeypatch.setattr(proof, "_latest_test_evidence", _test_evidence)
    monkeypatch.setattr(proof, "_jules_skill_inventory", _jules_skills)
    state_path = tmp_path / "proof.json"

    result = proof.build_collaboration_proof(
        write_state=True,
        state_path=str(state_path),
    )

    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["state_path"] == str(state_path)
    assert saved["state_path"] == str(state_path)
    assert saved["requirement_audit"]
    assert saved["collaboration_workflow"]
