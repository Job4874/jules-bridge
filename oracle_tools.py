"""oracle_tools — compatibility shim.

All implementation has moved to modules/oracle_session.py.
This module re-exports the public API so existing callers are unaffected.

Deprecated: import directly from modules.oracle_session instead.
"""

from modules.oracle_session import (  # noqa: F401
    oracle_status,
    oracle_build_deploy,
    codex_handover_index,
)

__all__ = ["oracle_status", "oracle_build_deploy", "codex_handover_index"]
