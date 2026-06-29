#!/usr/bin/env python3
"""Safe Jules Bridge probe for evidence reports.

The bridge screenshot route returns a base64 image payload. This helper strips
large image blobs and sensitive fields before printing JSON so remote workers
can cite screenshot paths without creating unusable base64 diffs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:5000"
OMITTED_IMAGE = "<image_base64 omitted; use saved_path as screenshot evidence>"
SENSITIVE_KEY_PARTS = ("authorization", "token", "secret", "password", "api_key", "apikey")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_bridge_token(root: Path | None = None) -> str:
    """Load the bridge token without printing it."""
    env_token = os.environ.get("JULES_BRIDGE_TOKEN", "").strip()
    if env_token:
        return env_token

    bridge_path = (root or repo_root()) / "bridge.py"
    text = bridge_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"BRIDGE_TOKEN\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        raise RuntimeError("BRIDGE_TOKEN not found; set JULES_BRIDGE_TOKEN")
    return match.group(1)


def clean_base_url(value: str | None = None) -> str:
    base = (value or os.environ.get("JULES_BRIDGE_URL") or DEFAULT_BASE_URL).strip()
    return base.rstrip("/")


def build_url(path: str, base_url: str | None = None) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return clean_base_url(base_url) + path


def sanitize(value: Any) -> Any:
    """Remove base64 image bodies and redact sensitive-looking fields."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower == "image_base64":
                sanitized[key] = OMITTED_IMAGE
            elif any(part in key_lower for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def request_json(path: str, *, base_url: str | None = None, token: str | None = None) -> dict[str, Any]:
    """Call a bridge JSON endpoint and return the decoded response."""
    headers = {
        "Authorization": f"Bearer {token or load_bridge_token()}",
        "ngrok-skip-browser-warning": "true",
        "Accept": "application/json",
    }
    request = urllib.request.Request(build_url(path, base_url), headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    if not isinstance(data, dict):
        return {"value": data}
    return data


def summarize_tentacles(data: dict[str, Any]) -> dict[str, Any]:
    tentacles = data.get("tentacles") or []
    return {
        "status": "ok",
        "tentacles": len(tentacles) if isinstance(tentacles, list) else 0,
        "mandatory_read": data.get("mandatory_read"),
        "sample_routes": [
            item.get("route")
            for item in tentacles[:5]
            if isinstance(item, dict) and item.get("route")
        ],
    }


def summarize_oracle_status(data: dict[str, Any]) -> dict[str, Any]:
    instance = data.get("instance") or {}
    quantower = data.get("quantower") or {}
    telemetry = data.get("telemetry") or {}
    verify = data.get("verify") or {}
    return {
        "blockers": data.get("blockers"),
        "branch": data.get("branch"),
        "quantower_running": quantower.get("running"),
        "instance_exists": instance.get("exists"),
        "instance_id": instance.get("instance_id"),
        "state": instance.get("state"),
        "primary_symbol_label": instance.get("primary_symbol_label"),
        "symbol_bound": instance.get("symbol_bound"),
        "account_bound": bool(instance.get("account_bound")),
        "enable_live_trading": instance.get("enable_live_trading"),
        "enable_dry_run_mode": instance.get("enable_dry_run_mode"),
        "gates": data.get("gates"),
        "telemetry_file": telemetry.get("file"),
        "telemetry_last_write_utc": telemetry.get("last_write_utc"),
        "pipeline_active": telemetry.get("pipeline_active"),
        "verify_code": verify.get("code"),
        "verify_checks": verify.get("checks"),
        "next_actions": data.get("next_actions"),
    }


def command_paths(command: str) -> list[str]:
    return {
        "ping": ["/ping"],
        "tentacles": ["/tentacles"],
        "oracle-status": ["/oracle/status"],
        "screenshot": ["/ui/screenshot?save=true"],
        "session-log": ["/session/log"],
        "all": ["/ping", "/tentacles", "/oracle/status", "/ui/screenshot?save=true"],
    }[command]


def summarize(command: str, path: str, data: dict[str, Any]) -> dict[str, Any]:
    if path == "/tentacles":
        return summarize_tentacles(data)
    if path == "/oracle/status":
        return summarize_oracle_status(data)
    if path.startswith("/ui/screenshot"):
        return {
            "saved_path": data.get("saved_path"),
            "image_base64": OMITTED_IMAGE,
        }
    return sanitize(data)


def run(command: str, *, base_url: str | None = None, raw: bool = False) -> dict[str, Any]:
    output: dict[str, Any] = {}
    token = load_bridge_token()
    for path in command_paths(command):
        data = request_json(path, base_url=base_url, token=token)
        output[path] = sanitize(data) if raw else summarize(command, path, data)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely probe Jules Bridge routes.")
    parser.add_argument(
        "command",
        choices=("ping", "tentacles", "oracle-status", "screenshot", "session-log", "all"),
    )
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--raw", action="store_true", help="Print sanitized raw response shape")
    args = parser.parse_args(argv)

    try:
        print(json.dumps(run(args.command, base_url=args.base_url, raw=args.raw), indent=2))
        return 0
    except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
