# Jules Bridge — Reasoning Memory

> This file contains accumulated patterns, strategies, and resolved blockers for Jules' reasoning module.
> It follows the HRE protocol: Hypothesis, Route, Evidence.

## Resolved Blockers

### [20250611] Headless Browser Verification
- **Hypothesis**: Headless environments (like Cursor Cloud) cannot run `pyautogui` or launch full UI browsers like Edge for verification.
- **Route**: Check environment with `GET /health` and verify display availability.
- **Evidence**: `pyautogui` throws `KeyError: 'DISPLAY'` or similar when called without X server.
- **Resolution**: Use `stub` UI actions or server-side logs/API responses for verification instead of screenshots in headless sessions. Update `AGENTS.md` with Cloud-specific instructions.

### [20250611] Windows Path Backslashes
- **Hypothesis**: Python's `os.path.join` on Windows produces backslashes which can be incorrectly escaped in JSON or shell commands if not handled as raw strings.
- **Route**: Log raw path strings before usage in shell calls.
- **Evidence**: Shell returns "path not found" for `C:\Users\admin` but works for `C:/Users/admin`.
- **Resolution**: Always use forward slashes in code and configuration, or raw strings `r""` for Windows paths.

## Reasoning Strategies

### HRE Self-Unblocking Protocol
When blocked:
1. **Hypothesis**: Classify the blocker (Permission, Missing Tool, Environment, Bug).
2. **Route**: Pick the tool/file/route that can prove the hypothesis.
3. **Evidence**: Capture the exact output (Return code, stderr, log entry).
4. **Action**: If unblocked, record the learning here. If still blocked after 3 passes, escalate with the captured evidence.

## Common Surfaces for Diagnosis
- `GET /tentacles`: Available tools.
- `GET /session/log`: Recent action history.
- `context/05_gotchas.md`: Known landmines.
- `bridge.log`: Low-level error details.
