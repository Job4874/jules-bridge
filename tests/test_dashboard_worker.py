import time

import pytest

import modules.dashboard_command_worker as dashboard_command_worker
from modules.dashboard_commands import (
    admit_command,
    configure_store_root,
    get_command,
    process_pending_commands,
    reset_store_root,
)


@pytest.fixture
def command_store(tmp_path, monkeypatch):
    store_root = tmp_path / "jules-dashboard-worker-store"
    configure_store_root(store_root)
    monkeypatch.delenv("DASHBOARD_COMMAND_WORKER", raising=False)
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER_INTERVAL_S", "0.25")
    yield store_root
    dashboard_command_worker.stop_command_worker()
    reset_store_root()


def test_worker_defaults_off(command_store, monkeypatch):
    monkeypatch.delenv("DASHBOARD_COMMAND_WORKER", raising=False)

    assert dashboard_command_worker.worker_enabled() is False

    status = dashboard_command_worker.start_command_worker()
    assert status["started"] is False
    assert status["reason"] == "disabled"
    assert status["mode"] == "manual_tick"


def test_background_worker_starts_only_when_enabled(command_store, monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "1")

    status = dashboard_command_worker.start_command_worker()
    assert status["started"] is True
    assert status["running"] is True
    assert status["mode"] == "background"
    assert status["enabled"] is True


def test_worker_tick_processes_admitted_commands(command_store, monkeypatch):
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

    admitted = admit_command({"type": "break_test", "summary": "Manual tick"})
    command_id = admitted["command"]["commandId"]

    tick = dashboard_command_worker.tick_command_worker(limit=5)

    assert tick["ok"] is True
    assert tick["processed"] == 1
    assert tick["succeeded"] == 1
    assert tick["skipped"] == 0
    assert tick["lastCommandId"] == command_id
    assert tick["lastTickAt"]

    stored = get_command(command_id)
    assert stored["command"]["status"] == "succeeded"


def test_worker_status_returns_counts(command_store):
    admit_command({"type": "button_sweep", "summary": "Pending"})
    admit_command({"type": "proof_replay", "summary": "Another pending"})

    status = dashboard_command_worker.worker_status()

    assert status["ok"] is True
    assert status["workerId"]
    assert status["enabled"] is False
    assert status["mode"] == "manual_tick"
    assert status["pendingCount"] == 2
    assert status["runningCount"] == 0
    assert status["terminalCount"] == 0


def test_completed_command_is_not_rerun(command_store):
    admitted = admit_command({"type": "proof_replay", "summary": "Replay requested"})
    command_id = admitted["command"]["commandId"]
    first = process_pending_commands(limit=5)
    assert first["count"] == 1

    tick = dashboard_command_worker.tick_command_worker(limit=5)
    assert tick["processed"] == 0
    assert tick["skipped"] == 0

    stored = get_command(command_id)
    assert stored["command"]["status"] == "not_implemented"


def test_cancelled_command_is_skipped(command_store):
    admitted = admit_command({"type": "proof_replay", "summary": "Will cancel"})
    command_id = admitted["command"]["commandId"]

    from modules.dashboard_commands import cancel_command

    cancel_command(command_id)

    tick = dashboard_command_worker.tick_command_worker(limit=5)
    assert tick["processed"] == 0

    stored = get_command(command_id)
    assert stored["command"]["status"] == "cancelled"


def test_background_worker_processes_admitted_command(command_store, monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "1")
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

    admitted = admit_command({"type": "break_test", "summary": "Background worker"})
    command_id = admitted["command"]["commandId"]

    status = dashboard_command_worker.start_command_worker()
    assert status["started"] is True
    assert status["running"] is True

    deadline = time.time() + 3.0
    terminal_status = None
    while time.time() < deadline:
        stored = get_command(command_id)
        terminal_status = stored["command"]["status"]
        if terminal_status in {"succeeded", "failed", "blocked", "not_implemented", "cancelled"}:
            break
        time.sleep(0.1)

    dashboard_command_worker.stop_command_worker()
    assert terminal_status == "succeeded"


def test_worker_disabled_by_env_does_not_start_daemon(command_store, monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "0")

    status = dashboard_command_worker.start_command_worker()
    assert status["started"] is False
    assert status["reason"] == "disabled"

    admitted = admit_command({"type": "button_sweep", "summary": "Should stay admitted"})
    stored = get_command(admitted["command"]["commandId"])
    assert stored["command"]["status"] == "admitted"
