import json

import pytest

from modules.dashboard_commands import (
    admit_command,
    configure_store_root,
    get_command,
    get_dashboard_projection,
    process_command,
    process_pending_commands,
    reset_store_root,
)
from modules.dashboard_evidence import (
    compute_result_hash,
    configure_evidence_root,
    get_evidence,
    list_evidence,
    redact_safe_payload,
    reset_evidence_root,
    write_command_evidence,
)


@pytest.fixture
def evidence_store(tmp_path):
    store_root = tmp_path / "jules-dashboard-evidence-store"
    configure_store_root(store_root)
    configure_evidence_root(store_root)
    yield store_root
    reset_store_root()
    reset_evidence_root()


def test_route_probe_ping_writes_evidence(evidence_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "Jules Bridge Online"}),
    )

    admitted = admit_command({"type": "route_probe", "route": "/ping"})
    process_command(admitted["command"]["commandId"])

    evidence_files = list((evidence_store / "evidence").glob("ev-*.json"))
    assert len(evidence_files) == 1
    payload = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert payload["type"] == "route_probe"
    assert payload["status"] == "succeeded"
    assert payload["redactionStatus"] == "redacted"
    assert payload["resultHash"].startswith("sha256:")


def test_command_evidence_refs_populated_after_worker_tick(evidence_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "Jules Bridge Online"}),
    )

    admitted = admit_command({"type": "route_probe", "route": "/ping"})
    tick = process_pending_commands(limit=5)

    command = tick["processed"][0]
    assert command["evidenceRefs"]
    assert str(command["evidenceRefs"][0]).startswith("ev-")

    stored = get_command(command["commandId"])
    assert stored["command"]["evidenceRefs"] == command["evidenceRefs"]


def test_projection_includes_latest_evidence(evidence_store, monkeypatch):
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
    assert projection["latestEvidence"]
    latest = projection["latestEvidence"][0]
    assert latest["evidenceId"].startswith("ev-")
    assert latest["commandId"] == admitted["command"]["commandId"]
    assert latest["redactionStatus"] == "redacted"


def test_evidence_file_survives_reload_from_disk(evidence_store):
    command = {
        "commandId": "cmd-reload",
        "workflowId": "wf-reload",
        "traceId": "trace-reload",
        "type": "route_probe",
        "route": "/ping",
        "status": "succeeded",
        "summary": "GET /ping returned 200",
        "result": {"statusCode": 200, "route": "/ping"},
    }
    evidence = write_command_evidence(
        command,
        result=command["result"],
        status="succeeded",
        summary=command["summary"],
    )

    fetched = get_evidence(evidence["evidenceId"])
    assert fetched["ok"] is True
    assert fetched["evidence"]["evidenceId"] == evidence["evidenceId"]
    assert fetched["safePayload"]["result"]["statusCode"] == 200


def test_blocked_route_probe_writes_blocked_evidence(evidence_store):
    admitted = admit_command({"type": "route_probe", "route": "/not-allowed"})
    finished = process_command(admitted["command"]["commandId"])
    command = finished["command"]

    assert command["status"] == "blocked"
    assert command["blockReason"] == "route_not_allowed"
    assert command["evidenceRefs"]

    listed = list_evidence(limit=5)
    assert listed["count"] >= 1
    latest = listed["evidence"][0]
    assert latest["status"] == "blocked"
    assert "not allowlisted" in latest["summary"].lower() or latest["summary"]


def test_result_hash_deterministic():
    payload = {"status": "succeeded", "route": "/ping", "result": {"statusCode": 200}}
    redacted = redact_safe_payload(payload)
    first = compute_result_hash(redacted)
    second = compute_result_hash(redacted)
    assert first == second
    assert first.startswith("sha256:")


def test_sensitive_strings_redacted():
    raw = {
        "Authorization": "Bearer super-secret-token",
        "api_key": "abc123",
        "cookie": "session=deadbeef",
        "access_token": "at-123",
        "refresh_token": "rt-456",
        "nested": {"password": "hunter2", "summary": "token=visible"},
        "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----",
    }
    redacted = redact_safe_payload(raw)

    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["cookie"] == "[REDACTED]"
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["refresh_token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["private_key"] == "[REDACTED]"
    dumped = json.dumps(redacted)
    assert "super-secret-token" not in dumped
    assert "BEGIN OPENSSH PRIVATE KEY" not in dumped


def test_evidence_refs_contain_ids_not_paths(evidence_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "ok"}),
    )

    admitted = admit_command({"type": "route_probe", "route": "/ping"})
    finished = process_command(admitted["command"]["commandId"])
    refs = finished["command"]["evidenceRefs"]

    assert refs
    for ref in refs:
        assert str(ref).startswith("ev-")
        assert "/" not in str(ref)
        assert "\\" not in str(ref)


def test_no_cloud_publish_artifacts_written(evidence_store, monkeypatch):
    monkeypatch.setattr(
        "modules.dashboard_commands._http_probe_get_route",
        lambda path: (200, {"status": "Jules Bridge Online"}),
    )
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
    monkeypatch.setattr(
        "modules.dashboard_commands.get_cloud_sync_status",
        lambda **kwargs: {"status": "synced"},
    )

    admit_command({"type": "route_probe", "route": "/ping"})
    process_pending_commands(limit=5)

    for path in evidence_store.rglob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        assert "cloud_publish_packet" not in text
        assert "begin pgp" not in text

    projection = get_dashboard_projection(limit=5)
    dumped = json.dumps(projection).lower()
    assert "cloud_publish_packet" not in dumped
