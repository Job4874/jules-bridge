# Jules Bridge — Gotchas

> Context file 5 of 6. What goes wrong. Not comprehensive docs — just the landmines.
> Nick Ni: "I have 553 lines of gotchas. Instead of 10,000 lines of docs."

## bridge.py

- **`string_field(data, key, default=...)`** — use `default=""` not `default=None` for optional strings
- **`json_payload()`** — raises BridgeHTTPError(400) if body is not valid JSON; always wrap with `@route_errors`
- **`@route_errors`** — MUST be the first decorator after `@app.route` (innermost position)
- **`jsonify(dict(some_dataclass))`** — dataclasses are NOT auto-serializable; convert to dict first
- **Adding a new route** — must also add to the Postman collection and to `context/02_architecture.md` route table
- **`ROOT_DIR`** is the Jules Bridge project root — use it for all default paths
- **`LOG_PATH`** is defined at module level — don't redefine it in route handlers

## modules/__init__.py

- **Adding a new module** — must add BOTH the import AND the `__all__` entry
- **Order matters** — modules that depend on others must be imported after their dependencies
- **Never re-export private helpers** (those prefixed with `_`)

## fs_service

- **`grep(pattern, path)`** — pattern is Python `re` regex, not glob
- **`tail(path, lines=50)`** — returns last N lines from end of file; `lines` param is from the end
- **`list_dir(path)`** — does NOT recurse; use `grep` for recursive search
- **Encoding** — always `encoding="utf-8", errors="replace"` for reading text files on Windows

## shell_executor

- **PowerShell on Windows** — always use `["powershell", "-Command", cmd]` not `["pwsh", ...]`
- **Timeout** — default is 30s; long builds need `timeout=120` or more
- **Exit codes** — `returncode=0` does NOT mean the command succeeded on Windows (always check output too)
- **Stderr** — captured into `stderr` field; check it even when returncode=0

## oracle_session

- **`oracle_status()`** — NEVER raises; always returns dict with `error` key if something failed
- **Info XML path** — must exist before `oracle_build_deploy()` is called; verify with `Verify-OracleReplayReady.ps1`
- **Quantower process name** — `Starter.exe` (check via `Get-Process -Name Starter`)
- **DLL path** — `C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll` (hardcoded in `oracle_session.py`)
- **Build config** — always `-c Release -a x64`; Debug builds won't load in Quantower

## reasoning_module

- **LLM stubs** — `_h_module_call()` and `_l_module_call()` return deterministic stubs; swap with real LLM at integration
- **`reason(problem, budget=10)`** — budget is max L-level steps; keep under 20 to avoid token bloat
- **`ReasoningTrace.to_inbox_summary()`** — call this, not `.inbox_summary()` (no such method)
- **ACT halting** — if confidence > 0.85, halts early; this is intentional, not a bug
- **`plan_only()`** — does NOT run L module; use this for previewing plans without executing

## retrospective_module

- **`analyze_session()`** — reads bridge.log from `LOG_PATH`; if log doesn't exist, returns empty report
- **Memory files** — written to `memory/` in project root; create this dir manually or call `analyze_session` once
- **`record_test_evidence(output)`** — takes raw pytest stdout as string; pipe via `result.stdout`
- **Evidence path** — `memory/test_evidence.json` is the evidence store; `memory/` dir must exist
- **Domain classification** — if the word "oracle" appears in a learning, it goes to `memory/oracle.md`

## inbox_service

- **`inbox_read()`** — reads all `.md` files in `jules_inbox/`; sorted alphabetically
- **Message format** — each message is a markdown file; first `##` heading is the subject
- **`inbox_write()`** — creates new file with timestamp; does NOT overwrite existing messages

## Windows-specific

- **Paths** — always use raw strings `r"C:\path"` or forward slashes `"C:/path"` (avoid backslash escaping bugs)
- **`os.path.join` on Windows** — produces backslashes; Flask routes need forward slashes
- **PowerShell execution policy** — if scripts fail with "not digitally signed", add `-ExecutionPolicy Bypass`
- **File locking** — Windows locks files that are open; `oracle_status()` uses `try/except` on file reads
