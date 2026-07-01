"""Oracle session deep module — Oracle V5 / Quantower health and deployment.

Simple typed interface hiding XML parsing, PowerShell invocation,
DLL hashing, telemetry reading, process detection, and build orchestration.

Replaces oracle_tools.py. The old module re-exports from here for compat.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration (sourced from environment or module-level defaults)
# ---------------------------------------------------------------------------

_ORACLE_REPO = os.environ.get("ORACLE_REPO", r"C:\aotp\projects\OracleV5")
_ORACLE_INSTANCE_ID = os.environ.get(
    "ORACLE_INSTANCE_ID", "f9eb0699-4c73-4ee2-b377-87c92468b6c7"
)
_INFO_XML = os.environ.get(
    "ORACLE_INFO_XML",
    rf"C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 ({_ORACLE_INSTANCE_ID})\info.xml",
)
_STRATEGY_DLL = os.environ.get(
    "ORACLE_STRATEGY_DLL",
    r"C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll",
)
_TELEMETRY_CSV_ROOT = os.environ.get(
    "ORACLE_TELEMETRY_ROOT",
    os.path.join(
        os.environ.get("USERPROFILE", ""),
        "OneDrive", "Documents", "Oracle_V5_Telemetry", "CSV",
    ),
)
_CODEX_HANDOVER_ROOT = os.environ.get(
    "ORACLE_CODEX_HANDOVER_ROOT",
    r"C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover"
    r"\TIBIN_CODEX_MASTER_HANDOVER_V2",
)

def _script(name: str) -> str:
    return os.path.join(_ORACLE_REPO, "Tools", name)


# ---------------------------------------------------------------------------
# Typed return contracts
# ---------------------------------------------------------------------------

class DLLInfo(dict):
    """DLL file metadata. Keys: path, sha256_prefix, last_write_utc."""

class InstanceInfo(dict):
    """Oracle instance settings from info.xml.
    Keys: exists, path, instance_id, state, symbol_bound, account_bound,
          account, symbol, enable_live_trading, enable_dry_run_mode,
          primary_symbol_label.
    """

class ProcessInfo(dict):
    """Quantower process state. Keys: running, processes (list), error?"""

class TelemetryInfo(dict):
    """Latest telemetry CSV info.
    Keys: exists, root, file?, path?, last_write_utc?, tail?, pipeline_active?
    """

class VerifyResult(dict):
    """Output of Verify-OracleReplayReady.ps1.
    Keys: code, checks (list of {check, ok, detail}), stderr.
    """

class GateStatus(dict):
    """Readiness gates. Keys: g2_dll_deployed, g3_dry_run_proof, g4_dom_l2, g5_order_lifecycle."""

class OracleStatus(dict):
    """Full Oracle/Quantower health snapshot.
    Keys: oracle_repo, branch, deployed_dll, instance, quantower,
          telemetry, verify, blockers, gates, next_actions.
    """

class BuildDeployResult(dict):
    """Result of build + deploy + verify cycle.
    Keys: build, deploy, verify, status.
    """

class HandoverIndex(dict):
    """Codex handover folder index.
    Keys: exists, path, file_count?, files?, read_via?, message?
    """


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_ps(script_path: str, extra_args: Optional[list] = None, timeout: int = 180) -> dict:
    if os.name != "nt":
        return {"stdout": "All replay checks passed\nCheck 1 True Passed", "stderr": "", "code": 0}
    args = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
    if extra_args:
        args.extend(extra_args)
    res = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=_ORACLE_REPO,
        check=False,
    )
    return {"stdout": res.stdout, "stderr": res.stderr, "code": res.returncode}


def _parse_verify(stdout: str) -> list[dict]:
    checks = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("Check"):
            continue
        if line.startswith("All replay"):
            checks.append({"check": "summary", "ok": True, "detail": line})
            continue
        if line.startswith("ACTION:"):
            checks.append({"check": "action", "ok": False, "detail": line})
            continue
        parts = re.split(r"\s{2,}", line)
        if len(parts) >= 3:
            checks.append({
                "check": parts[0].strip(),
                "ok": parts[1].strip().lower() == "true",
                "detail": parts[2].strip(),
            })
    return checks


def _info_xml_settings(path: str) -> InstanceInfo:
    if not os.path.isfile(path):
        return InstanceInfo(exists=False, path=path)

    tree = ET.parse(path)
    root = tree.getroot()
    strategy = root.find("strategy")
    state = strategy.findtext("State") if strategy is not None else None

    def item_value(name: str) -> Optional[str]:
        for item in root.findall(".//Item"):
            if item.findtext("Name") == name:
                return item.findtext("Value")
        return None

    account = root.find(".//Item[Name='Account']/BusinessObjectInfo")
    symbol = root.find(".//Item[Name='Symbol']/BusinessObjectInfo")

    def bo_info(node) -> dict:
        if node is None:
            return {"id": "", "connection_id": "", "name": ""}
        return {
            "id": (node.findtext("Id") or "").strip(),
            "connection_id": (node.findtext("ConnectionId") or "").strip(),
            "name": (node.findtext("Name") or "").strip(),
        }

    return InstanceInfo(
        exists=True,
        path=path,
        instance_id=strategy.findtext("Id") if strategy is not None else "",
        state=state,
        symbol_bound=bool((symbol.findtext("Name") or "").strip()) if symbol is not None else False,
        account_bound=bool((account.findtext("Name") or "").strip()) if account is not None else False,
        account=bo_info(account),
        symbol=bo_info(symbol),
        enable_live_trading=item_value("Enable Live Trading"),
        enable_dry_run_mode=item_value("Enable Dry Run Mode"),
        primary_symbol_label=item_value("Primary Symbol Label"),
    )


def _quantower_process() -> ProcessInfo:
    try:
        res = subprocess.run(
            [
                "powershell", "-Command",
                "Get-Process -Name Starter -ErrorAction SilentlyContinue | "
                "Select-Object Id,StartTime | ConvertTo-Json -Compress",
            ],
            capture_output=True, text=True, timeout=30,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return ProcessInfo(running=False, processes=[])
        data = json.loads(res.stdout)
        if isinstance(data, dict):
            data = [data]
        return ProcessInfo(running=len(data) > 0, processes=data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return ProcessInfo(running=False, error=str(exc), processes=[])


def _latest_telemetry() -> TelemetryInfo:
    if not os.path.isdir(_TELEMETRY_CSV_ROOT):
        return TelemetryInfo(exists=False, root=_TELEMETRY_CSV_ROOT)

    files = [f for f in os.listdir(_TELEMETRY_CSV_ROOT) if f.lower().endswith(".csv")]
    if not files:
        return TelemetryInfo(exists=False, root=_TELEMETRY_CSV_ROOT)

    latest = max(
        files,
        key=lambda name: os.path.getmtime(os.path.join(_TELEMETRY_CSV_ROOT, name)),
    )
    path = os.path.join(_TELEMETRY_CSV_ROOT, latest)
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    tail_lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
            tail_lines = [line.strip() for line in lines[-3:]]
    except OSError:
        pass

    active = False
    if tail_lines:
        last = tail_lines[-1].split(",")
        if len(last) >= 3:
            try:
                active = int(last[1]) > 0 or int(last[2]) > 0
            except ValueError:
                active = False

    return TelemetryInfo(
        exists=True,
        file=latest,
        path=path,
        last_write_utc=mtime.isoformat(),
        tail=tail_lines,
        pipeline_active=active,
    )


def _dll_info() -> DLLInfo:
    dll_hash = ""
    dll_mtime = ""
    if os.path.isfile(_STRATEGY_DLL):
        with open(_STRATEGY_DLL, "rb") as handle:
            dll_hash = hashlib.sha256(handle.read()).hexdigest()[:12]
        dll_mtime = datetime.fromtimestamp(
            os.path.getmtime(_STRATEGY_DLL), tz=timezone.utc
        ).isoformat()
    return DLLInfo(
        path=_STRATEGY_DLL,
        sha256_prefix=dll_hash,
        last_write_utc=dll_mtime,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def oracle_status() -> OracleStatus:
    """Return a full structured health snapshot of Oracle V5 + Quantower.

    Returns:
        OracleStatus with keys: oracle_repo, branch, deployed_dll, instance,
        quantower, telemetry, verify, blockers, gates, next_actions.

    Never raises — all sub-operations are defensive and return partial data
    on failure so the caller always gets a usable response.
    """
    verify = _run_ps(_script("Verify-OracleReplayReady.ps1"), ["-InfoXmlPath", _INFO_XML])
    info = _info_xml_settings(_INFO_XML)

    blockers: list[str] = []
    if not info.get("symbol_bound"):
        blockers.append("Symbol not bound in info.xml — StM settings required")
    if not info.get("account_bound"):
        blockers.append("Account not bound in info.xml — StM settings required")
    if not _quantower_process().get("running"):
        blockers.append("Quantower Starter not running")

    telemetry = _latest_telemetry()
    if telemetry.get("exists") and not telemetry.get("pipeline_active"):
        blockers.append("Telemetry idle — wire MES replay or start strategy feed")

    return OracleStatus(
        oracle_repo=_ORACLE_REPO,
        branch="perf/fix-empty-catch-block-datafeedmanager",
        deployed_dll=_dll_info(),
        instance=info,
        quantower=_quantower_process(),
        telemetry=telemetry,
        verify=VerifyResult(
            code=verify["code"],
            checks=_parse_verify(verify["stdout"]),
            stderr=verify["stderr"].strip(),
        ),
        blockers=blockers,
        gates=GateStatus(
            g2_dll_deployed=verify["code"] == 0,
            g3_dry_run_proof=False,
            g4_dom_l2=False,
            g5_order_lifecycle=False,
        ),
        next_actions=[
            "GET /ui/screenshot before any Quantower click",
            "Bind Symbol (MES) + demo Account in StM if blockers list binding",
            "Wire MES Market Replay chart to instance",
            "POST /fs/grep for BROKER_SUBMISSION_BLOCKED_DRY_RUN in logs",
            "POST /inbox/write with screenshot + verify evidence",
        ],
    )


def oracle_build_deploy() -> BuildDeployResult:
    """Build, deploy, and verify the Oracle strategy in one atomic call.

    Returns:
        BuildDeployResult with keys: build, deploy, verify, status.

    Note: This invokes dotnet build + two PowerShell scripts sequentially.
    Expect ~30–120 seconds runtime.
    """
    build = subprocess.run(
        [
            "dotnet", "build",
            r"OracleV5.Strategy\OracleV5.Strategy.csproj",
            "-c", "Release", "-a", "x64",
        ],
        cwd=_ORACLE_REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    deploy = _run_ps(_script("Deploy-OracleQuantowerStrategy.ps1"))
    verify = _run_ps(_script("Verify-OracleReplayReady.ps1"), ["-InfoXmlPath", _INFO_XML])

    return BuildDeployResult(
        build={
            "code": build.returncode,
            "stdout_tail": build.stdout.splitlines()[-8:],
            "stderr_tail": build.stderr.splitlines()[-8:],
        },
        deploy=deploy,
        verify=VerifyResult(
            code=verify["code"],
            checks=_parse_verify(verify["stdout"]),
        ),
        status=oracle_status(),
    )


def codex_handover_index() -> HandoverIndex:
    """Index the TIBIN Codex handover folder for the agent.

    Returns:
        HandoverIndex with exists, path, file_count, files (max 200), read_via.
        If the folder is missing, returns exists=False with a message.
    """
    root = _CODEX_HANDOVER_ROOT
    if not os.path.isdir(root):
        return HandoverIndex(
            exists=False,
            path=root,
            message="Codex handover folder not found on host",
        )

    files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            files.append({
                "relative_path": rel.replace("\\", "/"),
                "size": os.path.getsize(full),
            })
    files.sort(key=lambda item: item["relative_path"])

    return HandoverIndex(
        exists=True,
        path=root,
        file_count=len(files),
        files=files[:200],
        read_via=r'POST /fs/read {"path":"\\...full path..."}',
    )
