from __future__ import annotations
import json
import re
import os
import subprocess
from pathlib import Path
from typing import Iterable

def _sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8", errors="replace")).hexdigest()


def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)



def _read_json_file(path: Path) -> dict:
    try:
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}



def _merge_unique(prefix: Iterable[str], values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in list(prefix) + list(values):
        text = str(value)
        if text and text not in seen:
            merged.append(text)
            seen.add(text)
    return merged



def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value or "session").strip("-") or "session"



def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
            )
            return
        except Exception:
            pass
    try:
        process.kill()
    except Exception:
        pass
