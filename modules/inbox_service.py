"""Inbox service deep module — operator ↔ Jules message exchange.

Simple typed interface hiding path construction, file I/O,
directory listing, and error semantics.
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class InboxMessage(dict):
    """A message read from jules_inbox/.

    Keys always present:
      file (str): basename of the file read
      content (str): full text of the file

    Error variant (404):
      error (str): description
      hint (str): guidance for the caller
      inbox_files (list[str]): available filenames
    """


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_INBOX_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jules_inbox",
)
_DEFAULT_READ_FILE = "OPERATOR_RESPONSE.md"
_DEFAULT_WRITE_FILE = "JULES_RESPONSE.md"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def inbox_read(
    file: str | None = None,
    inbox_dir: str | None = None,
) -> tuple[InboxMessage, int]:
    """Read a file from jules_inbox/.

    Args:
        file: Basename of the file to read.
              Defaults to 'OPERATOR_RESPONSE.md'.
        inbox_dir: Override the default inbox directory path.

    Returns:
        Tuple of (InboxMessage, http_status_code).
        On success: (InboxMessage with file+content, 200).
        On missing: (InboxMessage with error+hint+inbox_files, 404).
    """
    base = inbox_dir or _DEFAULT_INBOX_DIR
    name = _safe_basename(file, _DEFAULT_READ_FILE)
    path = os.path.join(base, name)

    if not os.path.isfile(path):
        available = sorted(
            f for f in os.listdir(base)
            if os.path.isfile(os.path.join(base, f))
        ) if os.path.isdir(base) else []
        return (
            InboxMessage(
                error=f"inbox file not found: {name}",
                hint="Playbooks and host paths use POST /fs/read with full path.",
                inbox_files=available,
            ),
            404,
        )

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return InboxMessage(file=name, content=handle.read()), 200


def inbox_write(
    content: str,
    file: str | None = None,
    inbox_dir: str | None = None,
) -> dict:
    """Write content to a file in jules_inbox/.

    Args:
        content: Text to write (may be empty).
        file: Basename of the target file.
              Defaults to 'JULES_RESPONSE.md'.
        inbox_dir: Override the default inbox directory path.

    Returns:
        dict with status and file keys.
    """
    base = inbox_dir or _DEFAULT_INBOX_DIR
    name = _safe_basename(file, _DEFAULT_WRITE_FILE)
    path = os.path.join(base, name)
    os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return {"status": "success", "file": name}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _safe_basename(file: str | None, default: str) -> str:
    """Return a safe basename, defaulting if file is None or empty."""
    if not file:
        return default
    name = os.path.basename(file)
    return name if name else default
