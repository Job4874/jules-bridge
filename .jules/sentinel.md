## 2026-07-23 - Authentication Bypass in bridge.py
**Vulnerability:** Sensitive endpoints (`/remote/*`, `/chat`, `/chat/test`) were explicitly exempted from the `@require_auth` decorator logic in `bridge.py`, meaning they did not require a valid `BRIDGE_TOKEN`.
**Learning:** Routes related to remote interactions (like screen capture or keystroke input) and chat functionalities were likely temporarily exposed during development or assumed to be local-only, bypassing the main authentication check.
**Prevention:** Regularly review exemption lists in authentication decorators (`@require_auth`, `@public`) and ensure they only apply to health checks, public diagnostics, and deliberately unauthenticated static content.
