from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class JulesTask(dict):
    """A normalized Jules task card."""


class JulesDispatchResult(dict):
    """Result of parsing and preparing Jules worker dispatch packets."""


class JulesLaunchResult(dict):
    """Result of launching prepared Jules worker packets."""


class JulesRemoteResult(dict):
    """Result of a Jules remote session CLI query."""


class JulesPreflightResult(dict):
    """Jules CLI installation, auth, and remote-readiness diagnostic."""


class JulesPullResult(dict):
    """Result of pulling one remote Jules session."""


class JulesCotResult(dict):
    """Completion-of-task ledger for prepared Jules packets."""


class JulesCycleResult(dict):
    """End-to-end Jules dispatch, launch, pull, and COT cycle result."""


class JulesWatchResult(dict):
    """Bounded Jules polling, pull, and completion-of-task watch result."""


class JulesFleetResult(dict):
    """One Jules worker-fleet scaling cycle result."""


class JulesFleetWatchResult(dict):
    """Bounded Jules fleet scaling, polling, pull, and COT watch result."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "jules_inbox" / "jules_dispatch"
_DEFAULT_STATE_FILE = "JULES_LAUNCH_STATE.json"
_DEFAULT_PULL_DIR = "JULES_REMOTE_PULLS"
_DEFAULT_COT_DIR = "JULES_COT_REPORTS"
_DEFAULT_COT_LEDGER = "JULES_COT_LEDGER.md"

_DEFAULT_WATCH_STATE = "JULES_WATCH_STATE.json"
_DEFAULT_FLEET_STATE = "JULES_FLEET_STATE.json"
_DEFAULT_FLEET_WATCH_STATE = "JULES_FLEET_WATCH_STATE.json"
_STALE_UNKNOWN_REMOTE_SECONDS = 10 * 60
_DEFAULT_INCLUDED_STATUSES = ("failed", "needs_review", "ready_for_review", "unknown")
_DEFAULT_ANTIGRAVITY_PROMPT_DIR = (
    r"C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover"
    r"\TIBIN_CODEX_MASTER_HANDOVER_V2\04_CODEX_PROMPTS"
)
_ANTIGRAVITY_LINE_RE = re.compile(
    r"^(?P<status>[^|]+)\|\s*Antigravity offload:\s*(?P<prompt>[^|]+?)\s*\|\s*repo=(?P<repo>.+?)\s*$",
    re.IGNORECASE,
)
_TASK_HEADINGS = (
    ("testing", "Testing Improvement Task"),
    ("performance", "Performance Optimization Task"),
    ("code_health", "Code Health Improvement Task"),
)
_STATUS_PRIORITY = {
    "failed": 0,
    "needs_review": 1,
    "ready_for_review": 2,
    "unknown": 3,
    "complete": 4,
}
_COMPLETED_COT_STATUSES = {"completed_reported", "pulled_output_reported"}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
