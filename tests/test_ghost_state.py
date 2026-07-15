"""Tests for ghost_state module."""
import json
import modules.ghost_state as gs


def test_lock_and_unlock_with_password(tmp_path, monkeypatch):
    state_file = tmp_path / "ghost_state.json"
    monkeypatch.setattr(gs, "ghost_state_path", lambda: state_file)
    monkeypatch.setattr(gs, "host_identity_inbox_path", lambda repo_root=None: tmp_path / "HOST_IDENTITY.json")

    locked = gs.lock_ghost("test-pass-123", repo_root=str(tmp_path))
    assert locked["status"] == "locked"
    assert gs.ghost_protected() is True
    assert gs.verify_unlock("wrong") is False
    assert gs.verify_unlock("test-pass-123") is True

    unlocked = gs.unlock_ghost("test-pass-123", repo_root=str(tmp_path))
    assert unlocked["status"] == "unlocked"
    assert gs.ghost_protected() is False

    inbox = json.loads((tmp_path / "HOST_IDENTITY.json").read_text(encoding="utf-8"))
    assert inbox["location"] == "school"
    assert inbox["ram_gb"] == 64


def test_host_identity_includes_remote_intro():
    identity = gs.get_host_identity()
    assert identity["ram_gb"] == 64
    assert identity["location"] == "school"
    assert "remote_access_intro" in identity
    assert "school" in identity["remote_access_intro"].lower()


def test_get_ghost_status_never_exposes_hash(tmp_path, monkeypatch):
    state_file = tmp_path / "ghost_state.json"
    monkeypatch.setattr(gs, "ghost_state_path", lambda: state_file)
    gs.lock_ghost("pw", repo_root=str(tmp_path))
    status = gs.get_ghost_status()
    assert status["ghost_locked"] is True
    assert "unlock_password_hash" not in status
    assert status["always_on_enforced"] is True
