"""Ghost mode lock and host identity for Jules Bridge fleet coordination.

Public interface:
    load_ghost_state() -> GhostState
    lock_ghost(password, **overrides) -> GhostState
    unlock_ghost(password) -> GhostState
    verify_unlock(password) -> bool
    ghost_protected() -> bool
    get_ghost_status() -> dict[str, Any]
    get_bridge_urls() -> dict[str, str]
    get_host_identity() -> HostIdentity
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GhostState(dict):
    """Keys: locked, unlock_password_hash, locked_at_utc, host_id, location, ram_gb."""


class HostIdentity(dict):
    """Keys: host_id, location, ram_gb, ghost_locked, remote_access_intro, hostname."""


DEFAULT_LOCATION = "school"
DEFAULT_RAM_GB = 64
DEFAULT_HOST_ID = "school-64gb"

REMOTE_ACCESS_INTRO = (
    "I am the Jules Bridge operator on Abdul's school computer (64 GB RAM). "
    "I run authorized development and automation tasks through the local bridge API. "
    "Remote access requires a valid BRIDGE_TOKEN. "
    "When prompted, I always identify this host, its location (school), and RAM (64 GB). "
    "Ghost mode keeps the bridge online with the display off until unlocked with the operator password."
)


def _user_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "JulesBridge"


def ghost_state_path() -> Path:
    return _user_data_root() / "ghost_state.json"


def host_identity_inbox_path(repo_root: str | None = None) -> Path:
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    return root / "jules_inbox" / "HOST_IDENTITY.json"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _default_state() -> dict[str, Any]:
    return {
        "locked": False,
        "unlock_password_hash": "",
        "locked_at_utc": None,
        "host_id": DEFAULT_HOST_ID,
        "location": DEFAULT_LOCATION,
        "ram_gb": DEFAULT_RAM_GB,
        "hostname": socket.gethostname(),
        "remote_access_intro": REMOTE_ACCESS_INTRO,
        "identity_disclosure_policy": (
            "Always explain who you are when remote agents or operators connect. "
            "Use remote_access_intro verbatim unless the operator asks for a shorter summary."
        ),
    }


def load_ghost_state() -> GhostState:
    """Load persisted ghost state; returns unlocked defaults when missing."""
    path = ghost_state_path()
    state = _default_state()
    if not path.is_file():
        return GhostState(state)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            state.update(raw)
    except (OSError, json.JSONDecodeError):
        pass
    return GhostState(state)


def _write_state(state: dict[str, Any]) -> GhostState:
    path = ghost_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return GhostState(state)


def _write_inbox_identity(state: dict[str, Any], repo_root: str | None = None) -> None:
    inbox_path = host_identity_inbox_path(repo_root)
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host_id": state.get("host_id", DEFAULT_HOST_ID),
        "location": state.get("location", DEFAULT_LOCATION),
        "ram_gb": state.get("ram_gb", DEFAULT_RAM_GB),
        "hostname": state.get("hostname", socket.gethostname()),
        "ghost_locked": bool(state.get("locked")),
        "remote_access_intro": state.get("remote_access_intro", REMOTE_ACCESS_INTRO),
        "identity_disclosure_policy": state.get("identity_disclosure_policy"),
        "bridge_urls": {
            "local": "http://127.0.0.1:5000",
            "remote": _public_bridge_url(),
        },
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    inbox_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def lock_ghost(password: str, repo_root: str | None = None, **overrides: Any) -> GhostState:
    """Lock ghost mode; requires password to unlock later. Hash only — never stores plaintext."""
    if not password or not password.strip():
        return GhostState({"status": "error", "error": "password required to lock ghost state"})
    state = _default_state()
    state.update(overrides)
    state["locked"] = True
    state["unlock_password_hash"] = _hash_password(password.strip())
    state["locked_at_utc"] = datetime.now(timezone.utc).isoformat()
    written = _write_state(state)
    _write_inbox_identity(state, repo_root)
    written["status"] = "locked"
    return GhostState(written)


def verify_unlock(password: str) -> bool:
    """Return True when password matches the stored ghost unlock hash."""
    state = load_ghost_state()
    if not state.get("locked"):
        return True
    stored = str(state.get("unlock_password_hash") or "")
    if not stored:
        return False
    return _hash_password(password.strip()) == stored


def unlock_ghost(password: str, repo_root: str | None = None) -> GhostState:
    """Unlock ghost mode when password matches."""
    if not verify_unlock(password):
        return GhostState({"status": "denied", "error": "invalid unlock password"})
    state = load_ghost_state()
    state["locked"] = False
    state["unlocked_at_utc"] = datetime.now(timezone.utc).isoformat()
    written = _write_state(state)
    _write_inbox_identity(state, repo_root)
    written["status"] = "unlocked"
    return GhostState(written)


def ghost_protected() -> bool:
    """True when ghost mode is locked and must not be stopped without password."""
    return bool(load_ghost_state().get("locked"))


def get_ghost_status() -> dict[str, Any]:
    """Safe ghost snapshot for HTTP routes — never exposes password hashes."""
    state = load_ghost_state()
    return {
        "ghost_locked": bool(state.get("locked")),
        "locked_at_utc": state.get("locked_at_utc"),
        "unlocked_at_utc": state.get("unlocked_at_utc"),
        "host_id": state.get("host_id", DEFAULT_HOST_ID),
        "location": state.get("location", DEFAULT_LOCATION),
        "ram_gb": state.get("ram_gb", DEFAULT_RAM_GB),
        "hostname": state.get("hostname", socket.gethostname()),
        "remote_access_intro": state.get("remote_access_intro", REMOTE_ACCESS_INTRO),
        "identity_disclosure_policy": state.get(
            "identity_disclosure_policy",
            _default_state()["identity_disclosure_policy"],
        ),
        "bridge_urls": {
            "local": "http://127.0.0.1:5000",
            "remote": _public_bridge_url(),
        },
        "always_on_enforced": bool(state.get("locked")),
    }


def _public_bridge_url() -> str:
    explicit = os.environ.get("NGROK_PUBLIC_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    domain = os.environ.get("NGROK_DOMAIN", "parade-marrow-pulp.ngrok-free.dev").strip()
    return f"https://{domain}"


def get_bridge_urls() -> dict[str, str]:
    """Local and remote bridge URLs for fleet cards and identity payloads."""
    return {
        "local": "http://127.0.0.1:5000",
        "remote": _public_bridge_url(),
    }


def get_host_identity() -> HostIdentity:
    """Host metadata for remote Jules agents and fleet coordination."""
    state = load_ghost_state()
    return HostIdentity(
        {
            "host_id": state.get("host_id", DEFAULT_HOST_ID),
            "location": state.get("location", DEFAULT_LOCATION),
            "ram_gb": state.get("ram_gb", DEFAULT_RAM_GB),
            "hostname": state.get("hostname", socket.gethostname()),
            "ghost_locked": bool(state.get("locked")),
            "remote_access_intro": state.get("remote_access_intro", REMOTE_ACCESS_INTRO),
            "identity_disclosure_policy": state.get(
                "identity_disclosure_policy",
                _default_state()["identity_disclosure_policy"],
            ),
            "bridge_urls": {
                "local": "http://127.0.0.1:5000",
                "remote": _public_bridge_url(),
            },
        }
    )
