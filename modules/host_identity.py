"""Host identity — stable machine label for Jules remote reach-out.

Reads JULES_IDENTITY / JULES_CONTEXT from the environment, optional
SYSTEM_ID.txt, and hardware hints so cloud Jules can tell which host answered.
"""

from __future__ import annotations

import os
import re
import socket
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_SYSTEM_ID_PATH = _ROOT / "SYSTEM_ID.txt"
_GPG_PUBLIC_PATH = _ROOT / "jules-gpg-public.asc"
_KEY_ID_RE = re.compile(r"/([0-9A-Fa-f]{16})")


def _read_system_id_file() -> str:
    try:
        return _SYSTEM_ID_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _ram_gb() -> float | None:
    try:
        import psutil  # pylint: disable=import-outside-toplevel

        total = psutil.virtual_memory().total
        return round(total / (1024**3), 1)
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    if os.name != "nt":
        return None

    try:
        import subprocess  # pylint: disable=import-outside-toplevel

        raw = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            stderr=subprocess.DEVNULL,
            timeout=10,
            text=True,
        ).strip()
        if raw.isdigit():
            return round(int(raw) / (1024**3), 1)
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    label = _read_system_id_file()
    match = re.search(r"(\d+)\s*GB", label, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _gpg_key_id() -> str | None:
    try:
        text = _GPG_PUBLIC_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _KEY_ID_RE.search(text)
    return match.group(1).upper() if match else None


def read_gpg_public_armor() -> str | None:
    """Return the exported public key block, if present."""
    try:
        text = _GPG_PUBLIC_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if "BEGIN PGP PUBLIC KEY BLOCK" not in text:
        return None
    return text


def get_host_identity() -> dict[str, Any]:
    """Build a stable identity payload for /host/identity and /ping."""
    env_identity = (os.environ.get("JULES_IDENTITY") or "").strip().strip("\"'")
    system_id = _read_system_id_file()
    ram = _ram_gb()
    hostname = socket.gethostname()
    context = (os.environ.get("JULES_CONTEXT") or "").strip().strip("\"'")
    if context not in ("[LOCAL]", "[REMOTE_VM]", "[SCHOOL_COMPUTE]"):
        context = "[SCHOOL_COMPUTE]" if ram and ram >= 32 else "[LOCAL]"

    identity_label = env_identity or system_id
    if not identity_label and ram is not None:
        if context == "[SCHOOL_COMPUTE]" or ram >= 32:
            identity_label = f"School-PC-RAM-{int(ram)}GB"
        else:
            identity_label = f"Laptop-PC-RAM-{int(ram)}GB"

    gpg_key_id = _gpg_key_id()
    return {
        "hostname": hostname,
        "identity": identity_label or hostname,
        "execution_context": context,
        "ram_gb": ram,
        "system_id_file": system_id or None,
        "gpg_key_id": gpg_key_id,
        "gpg_configured": gpg_key_id is not None,
        "repo_root": str(_ROOT),
    }


def get_gpg_public_payload() -> dict[str, Any]:
    """Return GPG public key metadata for remote GitHub registration."""
    armor = read_gpg_public_armor()
    identity = get_host_identity()
    return {
        "title": "jules",
        "key_id": identity.get("gpg_key_id"),
        "email_hint": "Job4874@users.noreply.github.com",
        "github_add_url": "https://github.com/settings/gpg/new",
        "public_key": armor,
        "configured": armor is not None,
        "paste_instructions": (
            "Title: jules. Key: paste the full public_key block on GitHub."
        ),
    }
