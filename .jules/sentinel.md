## 2025-02-28 - Remote Endpoints Missing Authorization
**Vulnerability:** The `/remote/*` endpoints in `bridge.py` are explicitly excluded from authorization checks in the `@app.before_request` handler. These endpoints allow unauthorized users to capture screenshots, execute keyboard/mouse inputs, and view system metrics.
**Learning:** These endpoints provide dangerous capabilities (like executing commands via `pyautogui`) without any token validation, representing a critical authorization bypass vulnerability.
**Prevention:** Do not exclude high-privilege endpoints from global authorization middleware without a specific, secure design reason, and always validate access to remote input functions.
