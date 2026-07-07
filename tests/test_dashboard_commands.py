import json

import pytest

import modules.dashboard_commands as dashboard_commands
from modules.dashboard_commands import (
    admit_command,
    cancel_command,
    configure_store_root,
    get_command,
    get_dashboard_projection,
    get_workflow,
    list_commands,
    list_workflows,
    reset_store_root,
    sanitize_projection_value,
)


@pytest.fixture
def command_store(tmp_path, monkeypatch):
    store_root = tmp_path / "jules-dashboard-store"
    configure_store_root(store_root)
    yield store_root
    reset_store_root()


def test_command_admitted_and_persisted(command_store):
    result = admit_command({"type": "button_sweep", "summary": "DOM sweep requested"})

    assert result["ok"] is True
    command = result["command"]
    assert command["status"] == "not_implemented"
    assert command["commandId"]
    assert command["workflowId"]
    assert command["traceId"]

    stored = get_command(command["commandId"])
    assert stored["ok"] is True
    assert stored["command"]["commandId"] == command["commandId"]

    listed = list_commands(limit=5)
    assert listed["count"] >= 1
    assert listed["commands"][0]["commandId"] == command["commandId"]


def test_command_blocked_when_route_unsupported(command_store):
    result = admit_command({"type": "chat_send", "summary": ""})

    assert result["ok"] is True
    assert result["command"]["status"] == "blocked"
    assert "no draft" in result["command"]["blockReason"].lower()


def test_command_cancel_updates_status(command_store):
    admitted = admit_command({"type": "proof_replay", "summary": "Replay requested"})
    command_id = admitted["command"]["commandId"]

    cancelled = cancel_command(command_id)

    assert cancelled["ok"] is True
    assert cancelled["command"]["status"] == "cancelled"
    assert cancelled["workflow"]["status"] == "cancelled"


def test_workflow_projection_aggregates_latest_commands(command_store, monkeypatch):
    admit_command({"type": "break_test", "summary": "Refresh status"})
    admit_command({"type": "route_probe", "route": "GET /dashboard/status", "summary": "Probe status"})

    monkeypatch.setattr(
        "modules.dashboard_commands.get_dashboard_status",
        lambda bridge_start_utc=None: {
            "ok": True,
            "online": True,
            "contract": {"name": "jules_dashboard_status", "version": 2, "transport": "poll"},
            "execution_context": "local",
            "cloud_sync": {"status": "synced", "summary": "clean"},
            "alliance": {"ready_to_execute_alliance": False},
            "cache_age_s": 0,
        },
    )
    monkeypatch.setattr(
        "modules.dashboard_commands.get_cloud_sync_status",
        lambda **kwargs: {"status": "synced", "summary": "clean"},
    )

    projection = get_dashboard_projection(limit=10)

    assert projection["ok"] is True
    assert len(projection["commands"]) >= 2
    assert len(projection["workflows"]) >= 1
    assert projection["bridgeHealth"]["ok"] is True
    assert projection["contract"]["name"] == "jules_dashboard_projection"


def test_projection_redacts_tokens_cookies_credentials():
    raw = {
        "Authorization": "Bearer super-secret-token",
        "api_key": "abc123",
        "cookie": "session=deadbeef",
        "nested": {"password": "hunter2", "summary": "token=visible"},
    }
    sanitized = sanitize_projection_value(raw)

    assert sanitized["Authorization"] == "<redacted>"
    assert sanitized["api_key"] == "<redacted>"
    assert sanitized["cookie"] == "<redacted>"
    assert sanitized["nested"]["password"] == "<redacted>"


def test_unsupported_command_type_rejected(command_store):
    result = admit_command({"type": "unknown_type"})

    assert result["ok"] is False
    assert result["error"] == "unsupported_command_type"


def test_get_workflow_round_trip(command_store):
    admitted = admit_command({"type": "button_sweep", "summary": "Sweep"})
    workflow_id = admitted["workflow"]["workflowId"]

    fetched = get_workflow(workflow_id)

    assert fetched["ok"] is True
    assert fetched["workflow"]["workflowId"] == workflow_id
    assert admitted["command"]["commandId"] in fetched["workflow"]["commandIds"]


def test_list_workflows_returns_recent(command_store):
    admit_command({"type": "button_sweep", "summary": "One"})
    admit_command({"type": "proof_replay", "summary": "Two"})

    result = list_workflows(limit=10)

    assert result["ok"] is True
    assert result["count"] >= 2


def test_generated_cloud_artifacts_remain_untracked(command_store, tmp_path):
    admit_command({"type": "publish_preview", "summary": "Preview only"})
    store_files = list(command_store.rglob("*.json"))
    assert store_files
    for path in store_files:
        rel = path.read_text(encoding="utf-8")
        assert "cloud_publish_packet" not in rel.lower() or "local_preview" in rel.lower()

    projection = get_dashboard_projection(limit=5)
    dumped = json.dumps(projection)
    assert "BEGIN PGP" not in dumped
    assert ".gpg" not in dumped
