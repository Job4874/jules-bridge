"""Filesystem deep module — read, write, tail, grep, list.

Simple typed interface hiding all filesystem complexity.
All path validation and error handling lives here; callers get
clean TypedDicts back.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class FSResult(dict):
    """TypedDict-style result for single-file operations.

    Keys always present:
      path (str): absolute path operated on
      content (str): file text content
      data (str): alias of content (legacy compat)
    Optional keys:
      offset (int): for read with offset
      lines (int): for tail — number of lines returned
      pattern (str): for grep — the pattern used
      matches (list): for grep — [{line, text}, ...]
    """


class ListEntry(dict):
    """One entry in a directory listing.

    Keys: name, path, is_dir, size (None for dirs)
    """


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read(path: str, offset: int = 0, limit: Optional[int] = None) -> FSResult:
    """Read a text file, optionally by line offset/limit.

    Args:
        path: Absolute path to the file.
        offset: First line to include (0-indexed). Default 0.
        limit: Max number of lines to return. None = all.

    Returns:
        FSResult with keys: path, offset, content, data.

    Raises:
        FileNotFoundError: if path does not exist.
        IsADirectoryError: if path points to a directory.
        PermissionError: if file is not readable.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}", path)
    if not os.path.isfile(path):
        raise IsADirectoryError(f"Path is not a file: {path}", path)

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        if limit is None:
            content = handle.read()
        else:
            all_lines = handle.readlines()
            content = "".join(all_lines[offset : offset + limit])

    result = FSResult(path=path, offset=offset, content=content, data=content)
    return result


def write(path: str, content: str) -> FSResult:
    """Write text content to a file, creating parent directories as needed.

    Args:
        path: Absolute path to write.
        content: UTF-8 text content.

    Returns:
        FSResult with keys: path, status.

    Raises:
        PermissionError: if path is not writable.
        OSError: for other OS-level failures.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return FSResult(path=path, status="success", content=content, data=content)


def tail(path: str, lines: int = 50) -> FSResult:
    """Return the last N lines of a file.

    Args:
        path: Absolute path to the file.
        lines: Number of tail lines to return.

    Returns:
        FSResult with keys: path, lines (actual count), content, data.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}", path)
    if not os.path.isfile(path):
        raise IsADirectoryError(f"Path is not a file: {path}", path)

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        all_lines = handle.readlines()

    tail_lines = all_lines[-lines:]
    content = "".join(tail_lines)
    return FSResult(path=path, lines=len(tail_lines), content=content, data=content)


def grep(path: str, pattern: str = "", max_matches: int = 50) -> FSResult:
    """Search a file for a regex pattern, returning matching lines.

    Args:
        path: Absolute path to the file.
        pattern: Regex pattern (case-insensitive). Empty string matches all.
        max_matches: Stop after this many matches.

    Returns:
        FSResult with keys: path, pattern, matches (list of {line, text}).

    Raises:
        re.error: if pattern is not valid regex.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}", path)
    if not os.path.isfile(path):
        raise IsADirectoryError(f"Path is not a file: {path}", path)

    regex = re.compile(pattern, re.IGNORECASE)
    matches = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            if regex.search(line):
                matches.append({"line": line_no, "text": line.rstrip()})
                if len(matches) >= max_matches:
                    break

    return FSResult(path=path, pattern=pattern, matches=matches,
                    content="", data="")


def list_dir(path: str) -> list:
    """List files and folders under a directory path.

    Args:
        path: Absolute path to directory.

    Returns:
        Sorted list of ListEntry dicts (dirs first, then files alpha).

    Raises:
        FileNotFoundError: if path does not exist.
        NotADirectoryError: if path is not a directory.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such directory: {path}", path)
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Path is not a directory: {path}", path)

    entries = []
    for name in os.listdir(path):
        full = os.path.join(path, name)
        entries.append(
            ListEntry(
                name=name,
                path=full,
                is_dir=os.path.isdir(full),
                size=os.path.getsize(full) if os.path.isfile(full) else None,
            )
        )
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries
