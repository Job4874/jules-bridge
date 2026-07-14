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

    terminal_status = None

    # We replace sleep with active waiting logic that's cleaner and shorter in timeout for the test
    deadline = time.time() + 2.0
    while time.time() < deadline:
        stored = get_command(command_id)
        if not stored.get("ok"):
            time.sleep(0.01)
            continue
        terminal_status = stored["command"]["status"]
        if terminal_status in {"succeeded", "failed", "blocked", "not_implemented", "cancelled"}:
            break
        time.sleep(0.01)

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


def test_poll_interval_value_error(monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER_INTERVAL_S", "invalid")
    assert dashboard_command_worker._poll_interval_s() == 1.0


def test_worker_loop_handles_exception(command_store, monkeypatch):
    import threading
    called = threading.Event()
    def fake_tick(**kwargs):
        called.set()
        raise Exception("intentional")
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "1")
    monkeypatch.setattr("modules.dashboard_command_worker.tick_command_worker", fake_tick)
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER_INTERVAL_S", "0.01")

    status = dashboard_command_worker.start_command_worker()
    assert status["started"] is True

    assert called.wait(timeout=2.0)

    dashboard_command_worker.stop_command_worker()


def test_start_command_worker_already_running(command_store, monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "1")

    status1 = dashboard_command_worker.start_command_worker()
    assert status1["started"] is True

    status2 = dashboard_command_worker.start_command_worker()
    assert status2["started"] is False
    assert status2["reason"] == "already_running"

    dashboard_command_worker.stop_command_worker()

def test_tick_command_worker_returns_deterministic_counts(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands.process_pending_commands",
        lambda bridge_start_utc=None, limit=5: {
            "processed": [{"commandId": "cmd-1"}],
            "processedCount": 1,
            "skipped": 0,
            "succeeded": 1,
            "failed": 0,
            "blocked": 0,
            "not_implemented": 0,
        },
    )

    result = dashboard_command_worker.tick_command_worker()
    assert result["ok"] is True
    assert result["processed"] == 1
    assert result["succeeded"] == 1
    assert result["lastCommandId"] == "cmd-1"
    assert result["lastTickAt"] is not None


def test_worker_enabled_various_formats(monkeypatch):
    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "True")
    assert dashboard_command_worker.worker_enabled() is True

    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "yes")
    assert dashboard_command_worker.worker_enabled() is True

    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "on")
    assert dashboard_command_worker.worker_enabled() is True

    monkeypatch.setenv("DASHBOARD_COMMAND_WORKER", "0")
    assert dashboard_command_worker.worker_enabled() is False

def test_worker_status_reflects_counts(command_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands.get_command_status_counts",
        lambda: {
            "pendingCount": 5,
            "runningCount": 2,
            "terminalCount": 10,
        }
    )

    status = dashboard_command_worker.worker_status()
    assert status["pendingCount"] == 5
    assert status["runningCount"] == 2
    assert status["terminalCount"] == 10
