"""Tests for persistent Jules environment handling."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from modules import jules_env


@pytest.fixture
def env_paths(tmp_path, monkeypatch):
    repo_env = tmp_path / ".env"
    mirror_dir = tmp_path / "mirror"
    mirror_env = mirror_dir / ".env"
    token_file = mirror_dir / "ngrok_authtoken"
    monkeypatch.setattr(jules_env, "REPO_ENV_PATH", repo_env)
    monkeypatch.setattr(jules_env, "MIRROR_DIR", mirror_dir)
    monkeypatch.setattr(jules_env, "MIRROR_ENV_PATH", mirror_env)
    monkeypatch.setattr(jules_env, "NGROK_TOKEN_FILE", token_file)
    return repo_env, mirror_env, token_file


def test_ensure_bridge_token_never_rotates_existing(env_paths):
    repo_env, mirror_env, _ = env_paths
    repo_env.write_text("BRIDGE_TOKEN=keep-me\n", encoding="utf-8")
    token = jules_env.ensure_bridge_token()
    assert token == "keep-me"
    assert repo_env.read_text(encoding="utf-8") == "BRIDGE_TOKEN=keep-me\n"


def test_ensure_bridge_token_generates_when_missing(env_paths):
    repo_env, _, _ = env_paths
    token = jules_env.ensure_bridge_token()
    assert token
    assert f"BRIDGE_TOKEN={token}" in repo_env.read_text(encoding="utf-8")


def test_restore_env_from_mirror(env_paths):
    repo_env, mirror_env, _ = env_paths
    repo_env.write_text("", encoding="utf-8")
    mirror_env.parent.mkdir(parents=True, exist_ok=True)
    mirror_env.write_text("JULES_API_KEY=mirror-key\n", encoding="utf-8")
    restored = jules_env.restore_env_from_mirror(keys=("JULES_API_KEY",))
    assert restored["JULES_API_KEY"] == "mirror-key"
    assert "JULES_API_KEY=mirror-key" in repo_env.read_text(encoding="utf-8")


def test_sync_env_mirror(env_paths):
    repo_env, mirror_env, _ = env_paths
    repo_env.write_text("BRIDGE_TOKEN=repo-token\nLOCAL_BRIDGE_TOKEN=repo-token\n", encoding="utf-8")
    copied = jules_env.sync_env_mirror(keys=("BRIDGE_TOKEN", "LOCAL_BRIDGE_TOKEN"))
    assert copied["BRIDGE_TOKEN"] == "repo-token"
    assert "BRIDGE_TOKEN=repo-token" in mirror_env.read_text(encoding="utf-8")


@patch("pyngrok.ngrok.set_auth_token")
def test_configure_ngrok_auth_uses_env(mock_set_token, env_paths, monkeypatch):
    repo_env, _, token_file = env_paths
    repo_env.write_text("NGROK_AUTHTOKEN=abc123\n", encoding="utf-8")
    monkeypatch.setenv("NGROK_AUTHTOKEN", "abc123")
    with patch("shutil.which", return_value=None):
        ok, detail = jules_env.configure_ngrok_auth()
    assert ok is True
    mock_set_token.assert_called_once_with("abc123")
    assert detail == "ngrok authtoken configured"


def test_store_ngrok_authtoken_writes_all_locations(env_paths):
    repo_env, mirror_env, token_file = env_paths
    jules_env.store_ngrok_authtoken("secret-token")
    assert "NGROK_AUTHTOKEN=secret-token" in repo_env.read_text(encoding="utf-8")
    assert "NGROK_AUTHTOKEN=secret-token" in mirror_env.read_text(encoding="utf-8")
    assert token_file.read_text(encoding="utf-8").strip() == "secret-token"
    assert os.environ["NGROK_AUTHTOKEN"] == "secret-token"
