from pathlib import Path

from modules.tiu_workbench import build_tiu_workbench_plan


def _codebase_ready():
    return {
        "status": "ready",
        "summary": {
            "route_count": 76,
            "module_count": 34,
            "test_count": 45,
            "integration_ready_count": 9,
        },
    }


def _alliance_ready():
    return {
        "status": "ready",
        "summary": "8/8 switchboard gates passed.",
        "roles": {"mode": "two_agent_alliance"},
        "active_implementer": {"name": "antigravity_cli"},
        "completion_assessment": {
            "ready_to_execute_alliance": True,
            "safe_to_launch_live_work": False,
        },
    }


def _cloud_sync_blocked():
    return {
        "status": "blocked",
        "state": "blocked",
        "repo": {"branch": "master", "upstream": "origin/master", "remote_host": "github.com"},
        "git": {"ahead": 0, "behind": 0, "dirty_count": 45},
        "github": {"authenticated": True},
        "publish_ready": False,
        "synced": False,
        "blockers": ["dirty_worktree"],
        "warnings": ["remote_tracking_stale"],
    }


def _cloud_sync_clean():
    return {
        "status": "ready",
        "state": "synced",
        "repo": {"branch": "master", "upstream": "origin/master", "remote_host": "github.com"},
        "git": {"ahead": 0, "behind": 0, "dirty_count": 0},
        "github": {"authenticated": True},
        "publish_ready": False,
        "synced": True,
        "blockers": [],
        "warnings": [],
    }


def test_tiu_workbench_blocks_publish_when_cloud_sync_is_dirty(monkeypatch):
    monkeypatch.setattr("modules.tiu_workbench.analyze_codebase", lambda **kwargs: _codebase_ready())
    monkeypatch.setattr("modules.tiu_workbench.get_cloud_sync_status", lambda **kwargs: _cloud_sync_blocked())
    monkeypatch.setattr("modules.tiu_workbench.build_alliance_switchboard", lambda **kwargs: _alliance_ready())

    result = build_tiu_workbench_plan("Make the dashboard easier to operate.")

    assert result["status"] == "blocked"
    assert result["plan_state"] == "publish_blocked"
    assert "cloud_sync:dirty_worktree" in result["blockers"]
    assert result["readiness"]["codebase"]["route_count"] == 76
    assert result["target_files"][0] == "dashboard-ui/src/App.jsx"
    assert "BLOCKED: cloud_sync:dirty_worktree" in result["packet"]
    assert result["safety_policy"]["git_mutations"] is False


def test_tiu_workbench_can_generate_review_packet_without_cloud_gate(monkeypatch):
    monkeypatch.setattr("modules.tiu_workbench.analyze_codebase", lambda **kwargs: _codebase_ready())
    monkeypatch.setattr("modules.tiu_workbench.get_cloud_sync_status", lambda **kwargs: _cloud_sync_blocked())
    monkeypatch.setattr("modules.tiu_workbench.build_alliance_switchboard", lambda **kwargs: _alliance_ready())

    result = build_tiu_workbench_plan(
        "Prepare an interface review packet.",
        model_lane="gemini_cli",
        scope="model_bridge",
        require_cloud_sync=False,
    )

    assert result["status"] == "ready"
    assert result["plan_state"] == "ready_with_warnings"
    assert result["warnings"] == ["live_work_gated", "cloud_sync_gate_not_required_by_packet", "cloud_sync:remote_tracking_stale"]
    assert result["target_files"][0] == "modules/gemini_cli.py"
    assert "cloud_sync_required: false" in result["packet"]


def test_tiu_workbench_writes_repo_local_packet(monkeypatch, tmp_path):
    monkeypatch.setattr("modules.tiu_workbench.analyze_codebase", lambda **kwargs: _codebase_ready())
    monkeypatch.setattr("modules.tiu_workbench.get_cloud_sync_status", lambda **kwargs: _cloud_sync_clean())
    monkeypatch.setattr("modules.tiu_workbench.build_alliance_switchboard", lambda **kwargs: _alliance_ready())
    monkeypatch.setattr("modules.tiu_workbench._ROOT", tmp_path)
    monkeypatch.setattr("modules.tiu_workbench._DEFAULT_OUTPUT_DIR", tmp_path / "jules_inbox" / "tiu_workbench")

    result = build_tiu_workbench_plan("Save a local TIU packet.", write_packet=True)

    assert result["status"] == "ready"
    assert result["artifacts"]["packet_written"] is True
    assert Path(result["artifacts"]["packet_path"]).exists()
    assert Path(result["artifacts"]["state_path"]).exists()
    assert "TIU Workbench Packet" in Path(result["artifacts"]["packet_path"]).read_text(encoding="utf-8")
