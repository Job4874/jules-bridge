import json

import modules.alliance_switchboard as alliance


def _ready_jules():
    return {
        "ready": True,
        "installed": True,
        "likely_blocker": "",
        "rest_api": True,
        "auth_indicators": {"source": "test"},
    }


def _ready_antigravity():
    return {
        "ready": True,
        "installed": True,
        "likely_blocker": "",
        "capabilities": {
            "headless_mode": "-p/--print",
            "subcommands": ["plugin", "models"],
            "models": {"stdout": "Gemini 3.5 Flash\n"},
        },
    }


def _ready_gemini():
    return {
        "ready": False,
        "installed": True,
        "likely_blocker": "legacy_auth_required",
        "capabilities": {"skills": {"stdout": ""}},
    }


def _ready_akc():
    return {
        "ready": True,
        "status": "ready",
        "checkpoint_path": "context/08_akc_context_checkpoint.md",
        "missing_required_rules": [],
    }


def _proof():
    return {
        "status": "pass",
        "agents": {
            "antigravity": {"skills": [{"name": "plugin-management", "description": "Plugins", "location": "agy plugin"}]},
            "gemini": {"skills": [{"name": "skill-discovery", "description": "Skills", "location": "gemini skills"}]},
        },
    }


def _patch_ready(monkeypatch):
    monkeypatch.setattr(alliance, "jules_preflight", lambda **kwargs: _ready_jules())
    monkeypatch.setattr(alliance, "antigravity_preflight", lambda **kwargs: _ready_antigravity())
    monkeypatch.setattr(alliance, "gemini_preflight", lambda **kwargs: _ready_gemini())
    monkeypatch.setattr(alliance, "check_akc_readiness", lambda: _ready_akc())
    monkeypatch.setattr(alliance, "_read_json", lambda path: _proof())
    monkeypatch.setattr(
        alliance,
        "_jules_skills",
        lambda: [{"name": "architect", "description": "Plan features", "location": ".agents/skills/architect/SKILL.md"}],
    )


def test_switchboard_assigns_jules_creator_and_antigravity_implementer(monkeypatch):
    _patch_ready(monkeypatch)

    result = alliance.build_alliance_switchboard(
        objective="Create a complex codebase change",
        target_files=["bridge.py", "modules/"],
        include_live_checks=True,
    )

    assert result["status"] == "ready"
    assert result["roles"]["creator"]["agent"] == "jules"
    assert result["roles"]["implementer"]["agent"] == "antigravity_cli"
    assert result["roles"]["mode"] == "two_agent_alliance"
    assert result["active_implementer"]["selection"] == "preferred"
    assert result["completion_assessment"]["ready_to_execute_alliance"] is True
    assert result["safety_policy"]["default_mode"] == "dry_run"


def test_switchboard_falls_back_to_legacy_gemini_when_antigravity_is_blocked(monkeypatch):
    _patch_ready(monkeypatch)
    monkeypatch.setattr(
        alliance,
        "antigravity_preflight",
        lambda **kwargs: {"ready": False, "installed": False, "likely_blocker": "agy_missing"},
    )

    result = alliance.build_alliance_switchboard(
        objective="Review a broad refactor",
        include_live_checks=True,
    )

    assert result["status"] == "partial"
    assert result["roles"]["implementer"]["agent"] == "gemini_cli_legacy"
    assert result["active_implementer"]["selection"] == "fallback"
    assert any(gate["name"] == "preferred_implementer_reachable" and gate["status"] == "partial" for gate in result["gates"])


def test_switchboard_blocks_without_objective(monkeypatch):
    _patch_ready(monkeypatch)

    result = alliance.build_alliance_switchboard(
        objective="",
        include_live_checks=True,
    )

    assert result["status"] == "blocked"
    assert any(gate["name"] == "objective_present" and gate["status"] == "blocked" for gate in result["gates"])


def test_switchboard_writes_role_packets(monkeypatch, tmp_path):
    _patch_ready(monkeypatch)

    result = alliance.build_alliance_switchboard(
        objective="Coordinate Jules and Antigravity on a patch",
        include_live_checks=True,
        write_packets=True,
        state_path=str(tmp_path),
    )

    assert result["packets"]["written"] is True
    state_path = tmp_path / "ALLIANCE_SWITCHBOARD_STATE.json"
    creator_path = tmp_path / "ALLIANCE_CREATOR_JULES.md"
    implementer_path = tmp_path / "ALLIANCE_IMPLEMENTER_GOOGLE_TERMINAL.md"
    policy_path = tmp_path / "ALLIANCE_SWITCHING_POLICY.md"
    assert state_path.is_file()
    assert creator_path.is_file()
    assert implementer_path.is_file()
    assert policy_path.is_file()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["roles"]["implementer"]["agent"] == "antigravity_cli"
