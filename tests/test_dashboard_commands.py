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
    list_pending_commands,
    list_workflows,
    process_command,
    process_pending_commands,
    reset_store_root,
    sanitize_projection_value,
    update_command_status,
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
    assert command["status"] == "admitted"
    assert command["commandId"]
    assert command["workflowId"]
    assert command["traceId"]

    processed = process_pending_commands(limit=5)
    assert processed["count"] == 1
    command = processed["processed"][0]
    assert command["status"] == "not_implemented"

    stored = get_command(command["commandId"])
    assert stored["ok"] is True
    assert stored["command"]["commandId"] == command["commandId"]

    listed = list_commands(limit=5)
    assert listed["count"] >= 1
    assert listed["commands"][0]["commandId"] == command["commandId"]


def test_command_blocked_when_route_unsupported(command_store):
    result = admit_command({"type": "chat_send", "summary": ""})

    assert result["ok"] is True
    assert result["command"]["status"] == "admitted"

    processed = process_pending_commands(limit=5)
    command = processed["processed"][0]
    assert command["status"] == "blocked"
    assert "no draft" in command["blockReason"].lower()


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
    process_pending_commands(limit=5)

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
    assert projection["commandWorker"]["mode"] == "manual_tick"
    assert projection["commandWorker"]["workerId"]
    assert projection["commandWorker"]["pendingCount"] >= 0


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
    process_pending_commands(limit=5)
    store_files = list(command_store.rglob("*.json"))
    assert store_files
    for path in store_files:
        rel = path.read_text(encoding="utf-8")
        assert "cloud_publish_packet" not in rel.lower() or "local_preview" in rel.lower()

    projection = get_dashboard_projection(limit=5)
    dumped = json.dumps(projection)
    assert "BEGIN PGP" not in dumped
    assert ".gpg" not in dumped


def test_command_worker_lifecycle_admitted_running_terminal(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands.get_dashboard_status",
        lambda bridge_start_utc=None: {
            "ok": True,
            "online": True,
            "contract": {"name": "jules_dashboard_status", "version": 2},
            "execution_context": "local",
            "cloud_sync": {"status": "synced"},
            "cache_age_s": 0,
        },
    )

    admitted = admit_command({"type": "break_test", "summary": "Worker lifecycle"})
    command_id = admitted["command"]["commandId"]
    assert admitted["command"]["status"] == "admitted"
    assert list_pending_commands(limit=5)[0]["commandId"] == command_id

    running = update_command_status(command_id, "running", summary="Worker picked up command")
    assert running["ok"] is True
    assert running["command"]["status"] == "running"

    finished = process_command(command_id)
    assert finished["ok"] is True
    assert finished["command"]["status"] == "succeeded"
    assert finished["workflow"]["status"] == "succeeded"


def test_process_command_skips_terminal_status(command_store):
    admitted = admit_command({"type": "proof_replay", "summary": "Replay requested"})
    command_id = admitted["command"]["commandId"]
    process_pending_commands(limit=5)

    skipped = process_command(command_id)
    assert skipped["ok"] is True
    assert skipped["skipped"] is True
    assert skipped["command"]["status"] == "not_implemented"


def test_route_probe_ping_succeeds(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "Jules Bridge Online"}),
    )

    admitted = admit_command({"type": "route_probe", "route": "/ping", "summary": "Probe ping"})
    finished = process_command(admitted["command"]["commandId"])

    command = finished["command"]
    assert command["status"] == "succeeded"
    assert command["route"] == "/ping"
    assert command["result"]["statusCode"] == 200
    assert command["result"]["route"] == "/ping"
    assert command["summary"] == "GET /ping returned 200"
    assert command["evidenceRefs"]
    assert str(command["evidenceRefs"][0]).startswith("ev-")


def test_route_probe_dashboard_status_succeeds(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands.get_dashboard_status",
        lambda bridge_start_utc=None: {
            "ok": True,
            "contract": {"name": "jules_dashboard_status", "version": 2},
        },
    )

    admitted = admit_command({"type": "route_probe", "route": "/dashboard/status"})
    finished = process_command(admitted["command"]["commandId"])

    command = finished["command"]
    assert command["status"] == "succeeded"
    assert command["route"] == "/dashboard/status"
    assert command["result"]["statusCode"] == 200
    assert command["summary"] == "GET /dashboard/status returned 200"


def test_route_probe_external_url_blocked(command_store):
    admitted = admit_command({"type": "route_probe", "route": "https://example.com/ping"})
    finished = process_command(admitted["command"]["commandId"])

    command = finished["command"]
    assert command["status"] == "blocked"
    assert command["blockReason"] == "route_not_allowed"


def test_route_probe_non_allowlisted_internal_route_blocked(command_store):
    admitted = admit_command({"type": "route_probe", "route": "/not-allowed"})
    finished = process_command(admitted["command"]["commandId"])

    command = finished["command"]
    assert command["status"] == "blocked"
    assert command["blockReason"] == "route_not_allowed"
    assert command["route"] == "/not-allowed"


def test_route_probe_result_is_redacted(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (
            200,
            {
                "status": "ok",
                "Authorization": "Bearer super-secret-token",
                "api_key": "abc123",
                "cookie": "session=deadbeef",
            },
        ),
    )

    admitted = admit_command({"type": "route_probe", "route": "/ping"})
    finished = process_command(admitted["command"]["commandId"])
    result = finished["command"]["result"]

    assert result["Authorization"] == "<redacted>"
    assert result["api_key"] == "<redacted>"
    assert result["cookie"] == "<redacted>"


def test_projection_shows_succeeded_route_probe_terminal_state(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "Jules Bridge Online"}),
    )
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

    admitted = admit_command({"type": "route_probe", "route": "/ping"})
    process_command(admitted["command"]["commandId"])

    projection = get_dashboard_projection(limit=10)
    latest = next(item for item in projection["commands"] if item["commandId"] == admitted["command"]["commandId"])

    assert latest["status"] == "succeeded"
    assert latest["type"] == "route_probe"
    assert latest["route"] == "/ping"
    assert latest["result"]["statusCode"] == 200
    assert latest["evidenceRefs"]
