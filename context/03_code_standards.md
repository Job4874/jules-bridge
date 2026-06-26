# Jules Bridge — Code Standards

> Context file 3 of 7. Python conventions for the Jules Bridge codebase.

## Language: Python 3.12

## Module Structure Template

Every new module MUST follow this structure:

```python
"""One-line description.

Longer explanation of what this module hides and why.

Public interface:
    function_a(args) -> TypedReturnA
    function_b(args) -> TypedReturnB
"""
from __future__ import annotations

# stdlib imports only at top
import os
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class MyResult(dict):
    """Keys: key_a, key_b, ..."""

# or use dataclasses for richer types:
@dataclass
class MyResult:
    field_a: str
    field_b: int

# ---------------------------------------------------------------------------
# Private helpers (prefixed with _)
# ---------------------------------------------------------------------------

def _private_helper(x: str) -> dict:
    ...

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def my_function(arg: str, optional: str = "") -> MyResult:
    """One-line summary.

    Args:
        arg: Description
        optional: Description

    Returns:
        MyResult with keys: ...

    Never raises — returns partial data on failure.
    """
    try:
        ...
    except Exception as exc:
        return MyResult(error=str(exc))
```

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Module files | `snake_case_module.py` | `oracle_session.py` |
| Classes | `PascalCase` | `OracleStatus` |
| Functions | `snake_case` | `oracle_status()` |
| Private functions | `_snake_case` | `_run_ps()` |
| Constants | `SCREAMING_SNAKE` | `_ORACLE_REPO` |
| Type aliases | `PascalCase` | `ProcessInfo` |

## Return Types

- **Dict subclass** for simple key-value results: `class OracleStatus(dict)`
- **Dataclass** for richer typed results with methods: `@dataclass class ReasoningTrace`
- **Never return raw dicts** from public interface — always use a named type

## Error Handling

```python
# CORRECT: Never raises, returns partial data
def my_func() -> MyResult:
    try:
        result = do_something()
        return MyResult(value=result, error=None)
    except Exception as exc:
        return MyResult(value=None, error=str(exc))

# WRONG: Raises — violates the module contract
def my_func():
    result = do_something()  # Can raise!
    return result
```

## Tests

- One test file per module: `tests/test_{module_name}.py`
- Test at the module boundary only — no mocking of internals
- Use classes to group: `class TestMyFunction:`
- Test the contract (what's documented), not the implementation

## Route Handler Template

```python
@app.route("/prefix/action", methods=["POST"])
@route_errors
def handler_name():
    """POST /prefix/action — One-line description.

    Body (JSON):
        field  (str, required): Description
        opt    (str, optional): Description

    Returns JSON with ...
    """
    data = json_payload()
    field = string_field(data, "field")
    opt = string_field(data, "opt", default="")

    result = modules.my_function(field, optional=opt)

    return jsonify(dict(result))
```

## File Layout Rules

- No file should exceed 500 lines (if it does, extract a helper or split)
- No route handler should exceed 30 lines (all logic goes in module)
- No magic numbers — use named constants
