#!/usr/bin/env python3
"""Authed HRM + collaboration proof supplement for runtime proof runs.

Saves:
  04-hrm-complex-reasoning-unauth.json
  04-hrm-complex-reasoning-authed.json
  12-collaboration-proof-authed.json

Uses Authorization: Bearer $BRIDGE_TOKEN for protected routes.
Falls back to the Flask test client when the live bridge is unreachable.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notify_email import load_env  # noqa: E402
from modules.reasoning_module import HRM_COLLABORATION_PROBLEM  # noqa: E402

DEFAULT_BASE_URL = "http://127.0.0.1:5000"


def _live_post(base_url: str, token: str) -> Callable[..., tuple[int, dict[str, Any] | None]]:
    def post(path: str, body: dict[str, Any] | None = None, auth: bool = False) -> tuple[int, dict[str, Any] | None]:
        payload = json.dumps(body or {}).encode("utf-8")
        request = urllib.request.Request(
            base_url.rstrip("/") + path,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        if auth and token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"error": raw}
            return exc.code, parsed

    return post


def _test_client_post(token: str) -> Callable[..., tuple[int, dict[str, Any] | None]]:
    os.environ.setdefault("BRIDGE_TOKEN", token or "JULES-SECURE-999")
    import bridge  # noqa: WPS433

    client = bridge.app.test_client()

    def post(path: str, body: dict[str, Any] | None = None, auth: bool = False) -> tuple[int, dict[str, Any] | None]:
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {os.environ['BRIDGE_TOKEN']}"
        response = client.post(path, json=body or {}, headers=headers)
        return response.status_code, response.get_json()

    return post


def main() -> int:
    load_env()
    token = os.environ.get("BRIDGE_TOKEN", "").strip()
    base_url = os.environ.get("JULES_BRIDGE_URL", DEFAULT_BASE_URL).strip()
    out_dir = ROOT / f"runtime-proof-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(exist_ok=True)

    use_live = os.environ.get("JULES_PROOF_USE_LIVE", "").strip().lower() in ("1", "true", "yes")
    if use_live:
        post = _live_post(base_url, token)
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/ping", timeout=2):
                pass
        except Exception:
            use_live = False

    if not use_live:
        post = _test_client_post(token)

    hrm_body = {
        "problem": HRM_COLLABORATION_PROBLEM,
        "model": "stub",
        "require_json": True,
        "halt_budget": 12,
    }
    unauth_status, unauth_payload = post("/reasoning/solve", hrm_body, auth=False)
    authed_status, authed_payload = post("/reasoning/solve", hrm_body, auth=True)
    collab_status, collab_payload = post("/proof/collaboration", {"write_state": False}, auth=True)

    (out_dir / "04-hrm-complex-reasoning-unauth.json").write_text(
        json.dumps({"status": unauth_status, **(unauth_payload or {})}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "04-hrm-complex-reasoning-authed.json").write_text(
        json.dumps(authed_payload or {}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "12-collaboration-proof-authed.json").write_text(
        json.dumps(collab_payload or {}, indent=2),
        encoding="utf-8",
    )

    hrm_gate = next(
        (gate for gate in (collab_payload or {}).get("gates", []) if gate.get("name") == "hrm_reasoning"),
        {},
    )
    print(f"proof_dir={out_dir}")
    print(f"unauth_status={unauth_status}")
    print(f"hrm_authed_status={authed_status}")
    print(f"hrm_succeeded={(authed_payload or {}).get('succeeded')}")
    print(f"hrm_trace_complete={((authed_payload or {}).get('trace') or {}).get('complete')}")
    print(f"hrm_reasoning_gate={hrm_gate.get('status')}")
    print(f"collab_status={(collab_payload or {}).get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
