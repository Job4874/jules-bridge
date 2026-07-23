# Security Review Notes — GitHub Suggestions Analysis

**Date:** 2026-07-23  
**Source:** GitHub Code Suggestions Beta  
**Status:** Under review — requires confirmation before fixes

---

## Overview

GitHub Suggestions flagged three security concerns in `bridge.py`. This document analyzes each one and recommends next steps.

---

## Finding #1: Path Traversal in Filesystem Read Route

**Flagged in:** `fs_service.read()`, `fs_service.write()`, `fs_service.tail()`, `fs_service.grep()`

### What I found

The `fs_service` functions accept arbitrary file paths as input without path normalization or prefix validation. A caller could theoretically pass `../../etc/passwd` or absolute paths outside an intended directory.

```python
# fs_service.py, line 47-76
def read(path: str, offset: int = 0, limit: Optional[int] = None) -> FSResult:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}", path)
    # ... opens path directly, no prefix check
```

### Actual Risk Level

**LOW → MEDIUM** depending on how bridge.py exposes these functions:

- **IF** the HTTP route handler validates/restricts paths (e.g., `allowed_base = "/data"; request.path.startswith(allowed_base)`) → **LOW** (path validation at boundary)
- **IF** the HTTP route accepts arbitrary paths from user input → **MEDIUM** (real traversal risk)

### Recommended Fix (if HIGH risk)

```python
import os

ALLOWED_BASE = os.path.abspath("/var/data/allowed")  # or configurable

def read(path: str, offset: int = 0, limit: Optional[int] = None) -> FSResult:
    resolved = os.path.abspath(path)
    if not resolved.startswith(ALLOWED_BASE):
        raise PermissionError(f"Path outside allowed directory: {path}")
    # ... rest of function
```

### Next Steps

- [ ] **Verify:** Check bridge.py routes that call `fs_service.read/write/tail/grep`. Do they validate/restrict paths before passing to `fs_service`?
- [ ] **Decide:** If routes already validate, this is defense-in-depth (add it anyway). If not, fix routes first, then add `fs_service` checks.

---

## Finding #2: Command Injection in Shell Executor

**Flagged in:** `shell_executor.execute()`, `shell_executor.spawn()`

### What I found

The `shell_executor` module passes user-provided commands to `subprocess.run()` and `subprocess.Popen()`. The current pattern is:

```python
# shell_executor.py, line 138-143, 198-203
resolved_shell, args = _build_args(shell, command)
proc = subprocess.Popen(
    args,  # args is a LIST, e.g. ["powershell.exe", "-Command", command]
    cwd=effective_cwd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

### Actual Risk Level

**LOW** (likely safe):

- ✅ Uses `subprocess.run(args=[...])` (list form), NOT `shell=True` → shell won't interpret `command`
- ✅ No shell metacharacters are evaluated; command goes directly to the process
- ⚠️ HOWEVER: if the command string is constructed from unsanitized user input before being passed to `_build_args()`, that could be an upstream problem

### What Could Go Wrong

```python
# SAFE (args list prevents injection):
subprocess.run(["cmd.exe", "/c", "echo $(evil)"], ...)  # outputs literal "$(evil)"

# UNSAFE (would only happen if caller constructs command unsafely):
user_input = "dir & del /s *"  # attacker input
command = f"cd {user_input}"    # string interpolation BEFORE passing to shell_executor
shell_executor.execute(command) # now executing "cd dir & del /s *"
```

### Next Steps

- [ ] **Verify:** Check all bridge.py routes that call `shell_executor.execute/spawn`. Are commands built safely, or constructed from user input?
- [ ] **If safe:** Document why (subprocess args list is safe; no string concatenation with user input).
- [ ] **If risky:** Refactor to use parameterized commands or argument lists instead of string interpolation.

---

## Finding #3: Authentication Bypass on Dashboard Commands

**Flagged in:** `@require_auth()` decorator and exempted routes

### What I found

The `@require_auth()` decorator on `bridge.py` has exceptions for several routes:

```python
# bridge.py, line 88-99
@app.before_request
def require_auth():
    if request.path.startswith("/remote/") or request.path in (
        "/health",
        "/ping",
        "/host/identity",
        "/ghost/status",
        "/dashboard/status",
        "/vm/status",
        "/chat",
        "/chat/test",
    ):
        return None  # NO AUTH REQUIRED
```

### Actual Risk Level

**LOW → MEDIUM** depending on what these unauthenticated routes do:

- ✅ `/health`, `/ping` → safe (diagnostics only)
- ✅ `/host/identity` → likely safe (public host info)
- ⚠️ `/chat`, `/chat/test` → risky (does this let unauthenticated users control LLM?)
- ⚠️ `/remote/*` → risky (exposes screen capture, keyboard/mouse control?)

### Recommended Review

For each unauthenticated route, ask: **"Could an attacker use this to control the workstation or access data?"**

- `/chat` without auth → potential LLM jailbreak or prompt injection
- `/remote/screen` without auth → information disclosure (see workstation screen)
- `/remote/input` without auth → keystroke injection (type commands, steal data)

### Next Steps

- [ ] **Audit:** Review each exempted route. Is it intentionally public? If not, move it behind auth.
- [ ] **Decision:** 
  - **If dashboard/remote are meant to be local-only:** add IP whitelist (127.0.0.1:5000 only)
  - **If dashboard/remote are meant to be internet-exposed:** require BRIDGE_TOKEN on all sensitive routes

---

## Recommendations

1. **Path Traversal**: Add `os.path.abspath()` normalization + prefix check in `fs_service` as defense-in-depth.
2. **Command Injection**: Audit `bridge.py` routes that build shell commands; document why subprocess args list prevents injection.
3. **Auth Bypass**: Review which routes are intentionally unauthenticated; apply stricter access controls to `/remote/*` and `/chat` if they're not meant to be public.

---

## Follow-up

This review is **not exhaustive**. It covers the three GitHub Suggestions but does not assess:
- CSRF protection (are state-changing routes protected?)
- Input validation (are JSON fields sanitized?)
- Error handling (do exceptions leak sensitive info?)
- Rate limiting (can attackers spam requests?)

A full security audit is recommended before using this bridge in production or on untrusted networks.
