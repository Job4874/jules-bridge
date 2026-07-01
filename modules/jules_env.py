"""Persistent Jules environment loading and secret mirroring.

Repo ``.env`` is canonical. ``~/.jules/.env`` is a durable mirror so tokens
survive repo moves, reinstalls, and vacation-mode unattended operation.
Existing values are never overwritten unless ``force`` is requested.
"""

from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_ENV_PATH = REPO_ROOT / ".env"
REPO_ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
MIRROR_DIR = Path.home() / ".jules"
MIRROR_ENV_PATH = MIRROR_DIR / ".env"
NGROK_TOKEN_FILE = MIRROR_DIR / "ngrok_authtoken"

PERSISTENT_KEYS: tuple[str, ...] = (
    "BRIDGE_TOKEN",
    "LOCAL_BRIDGE_TOKEN",
    "NGROK_AUTHTOKEN",
    "JULES_API_KEY",
    "JULES_SOURCE",
    "JULES_USE_REST_API",
    "JULES_API_BASE_URL",
    "JULES_STARTING_BRANCH",
    "JULES_IDENTITY",
    "JULES_CONTEXT",
    "GMAIL_USER",
    "GMAIL_APP_PASSWORD",
    "EMAIL_TO",
    "BROWSER_MODEL_LOOP_URL",
    "GCE_WORKER_IP",
    "GCE_WORKER_NAME",
    "GCE_WORKER_PROJECT",
    "GCE_WORKER_ZONE",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _merge_env_files(*paths: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        merged.update(_parse_env_file(path))
    return merged


def _set_env_value(path: Path, key: str, value: str, *, only_if_missing: bool = True) -> bool:
    values = _parse_env_file(path)
    if only_if_missing and values.get(key):
        return False
    values[key] = value
    _write_env_file(path, values)
    return True


def load_env() -> None:
    """Load mirror env first, then repo env. Repo values win on conflict."""
    for path in (MIRROR_ENV_PATH, REPO_ENV_PATH):
        if not path.is_file():
            continue
        for key, value in _parse_env_file(path).items():
            os.environ.setdefault(key, value)

    token_file = NGROK_TOKEN_FILE
    if token_file.is_file() and not os.environ.get("NGROK_AUTHTOKEN"):
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            os.environ["NGROK_AUTHTOKEN"] = token


def ensure_repo_env() -> None:
    if REPO_ENV_PATH.is_file():
        return
    if REPO_ENV_EXAMPLE_PATH.is_file():
        shutil.copyfile(REPO_ENV_EXAMPLE_PATH, REPO_ENV_PATH)
        return
    REPO_ENV_PATH.write_text("", encoding="utf-8")


def ensure_bridge_token() -> str:
    """Ensure BRIDGE_TOKEN exists and is never rotated automatically."""
    ensure_repo_env()
    merged = _merge_env_files(MIRROR_ENV_PATH, REPO_ENV_PATH)
    token = merged.get("BRIDGE_TOKEN", "").strip()
    if not token or token == "change-me-local-bridge-token":
        token = secrets.token_urlsafe(32)
        _set_env_value(REPO_ENV_PATH, "BRIDGE_TOKEN", token, only_if_missing=False)
        _set_env_value(MIRROR_ENV_PATH, "BRIDGE_TOKEN", token, only_if_missing=False)
    os.environ["BRIDGE_TOKEN"] = token
    return token


def ensure_local_bridge_token() -> str:
    bridge_token = ensure_bridge_token()
    merged = _merge_env_files(MIRROR_ENV_PATH, REPO_ENV_PATH)
    local_token = merged.get("LOCAL_BRIDGE_TOKEN", "").strip()
    if not local_token:
        _set_env_value(REPO_ENV_PATH, "LOCAL_BRIDGE_TOKEN", bridge_token, only_if_missing=True)
        _set_env_value(MIRROR_ENV_PATH, "LOCAL_BRIDGE_TOKEN", bridge_token, only_if_missing=True)
        local_token = bridge_token
    os.environ["LOCAL_BRIDGE_TOKEN"] = local_token
    return local_token


def store_ngrok_authtoken(token: str, *, force: bool = False) -> None:
    cleaned = token.strip()
    if not cleaned:
        raise ValueError("NGROK authtoken is empty")
    _set_env_value(REPO_ENV_PATH, "NGROK_AUTHTOKEN", cleaned, only_if_missing=not force)
    _set_env_value(MIRROR_ENV_PATH, "NGROK_AUTHTOKEN", cleaned, only_if_missing=not force)
    NGROK_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    NGROK_TOKEN_FILE.write_text(cleaned + "\n", encoding="utf-8")
    os.environ["NGROK_AUTHTOKEN"] = cleaned


def resolve_ngrok_authtoken() -> str:
    load_env()
    for key in ("NGROK_AUTHTOKEN", "NGROK_AUTH_TOKEN", "NGROK_TOKEN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    if NGROK_TOKEN_FILE.is_file():
        value = NGROK_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if value:
            os.environ["NGROK_AUTHTOKEN"] = value
            return value
    return ""


def configure_ngrok_auth() -> tuple[bool, str]:
    """Apply ngrok authtoken to pyngrok and the ngrok CLI config."""
    token = resolve_ngrok_authtoken()
    if not token:
        return False, "NGROK_AUTHTOKEN missing from .env and ~/.jules mirror"

    from pyngrok import ngrok  # pylint: disable=import-outside-toplevel

    ngrok.set_auth_token(token)

    ngrok_cmd = shutil.which("ngrok")
    if ngrok_cmd:
        import subprocess  # pylint: disable=import-outside-toplevel

        result = subprocess.run(
            [ngrok_cmd, "config", "add-authtoken", token],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 and "already" not in (result.stderr + result.stdout).lower():
            return False, (result.stderr or result.stdout or "ngrok config add-authtoken failed").strip()

    return True, "ngrok authtoken configured"


def sync_env_mirror(keys: Iterable[str] | None = None) -> dict[str, str]:
    """Copy persistent keys from repo .env into ~/.jules/.env without clobbering."""
    ensure_repo_env()
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    repo_values = _parse_env_file(REPO_ENV_PATH)
    mirror_values = _parse_env_file(MIRROR_ENV_PATH)
    selected = tuple(keys or PERSISTENT_KEYS)
    copied: dict[str, str] = {}
    for key in selected:
        value = repo_values.get(key, "").strip()
        if not value:
            continue
        if mirror_values.get(key) != value:
            mirror_values[key] = value
            copied[key] = value
    if copied:
        _write_env_file(MIRROR_ENV_PATH, mirror_values)
    return copied


def restore_env_from_mirror(keys: Iterable[str] | None = None) -> dict[str, str]:
    """Fill missing repo .env keys from ~/.jules/.env mirror."""
    ensure_repo_env()
    repo_values = _parse_env_file(REPO_ENV_PATH)
    mirror_values = _parse_env_file(MIRROR_ENV_PATH)
    selected = tuple(keys or PERSISTENT_KEYS)
    restored: dict[str, str] = {}
    for key in selected:
        if repo_values.get(key, "").strip():
            continue
        mirror_value = mirror_values.get(key, "").strip()
        if not mirror_value:
            continue
        repo_values[key] = mirror_value
        restored[key] = mirror_value
    if restored:
        _write_env_file(REPO_ENV_PATH, repo_values)
    return restored


def ensure_persistent_secrets(*, ngrok_authtoken: str = "", force_ngrok: bool = False) -> dict[str, object]:
    """One-shot boot prep: restore mirror, protect tokens, sync, configure ngrok."""
    ensure_repo_env()
    restored = restore_env_from_mirror()
    if ngrok_authtoken.strip():
        store_ngrok_authtoken(ngrok_authtoken, force=force_ngrok)
    bridge_token = ensure_bridge_token()
    local_token = ensure_local_bridge_token()
    copied = sync_env_mirror()
    ngrok_ok, ngrok_detail = configure_ngrok_auth()
    load_env()
    return {
        "ok": ngrok_ok,
        "bridge_token_present": bool(bridge_token),
        "local_bridge_token_present": bool(local_token),
        "restored_from_mirror": restored,
        "mirrored_to_jules_home": copied,
        "ngrok_configured": ngrok_ok,
        "ngrok_detail": ngrok_detail,
        "mirror_path": str(MIRROR_ENV_PATH),
        "repo_env_path": str(REPO_ENV_PATH),
    }
