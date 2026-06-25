"""Structured Oracle / Quantower helpers for the Jules bridge."""
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ORACLE_REPO = r"C:\aotp\projects\OracleV5"
ORACLE_INSTANCE_ID = "f9eb0699-4c73-4ee2-b377-87c92468b6c7"
INFO_XML = (
    rf"C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 ({ORACLE_INSTANCE_ID})\info.xml"
)
STRATEGY_DLL = r"C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll"
TELEMETRY_CSV_ROOT = os.path.join(
    os.environ.get("USERPROFILE", ""),
    "OneDrive",
    "Documents",
    "Oracle_V5_Telemetry",
    "CSV",
)
VERIFY_SCRIPT = os.path.join(ORACLE_REPO, "Tools", "Verify-OracleReplayReady.ps1")
DEPLOY_SCRIPT = os.path.join(ORACLE_REPO, "Tools", "Deploy-OracleQuantowerStrategy.ps1")
APPLY_PROFILE_SCRIPT = os.path.join(ORACLE_REPO, "Tools", "Apply-OracleReplayProfile.ps1")
CODEX_HANDOVER_ROOT = (
    r"C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover"
    r"\TIBIN_CODEX_MASTER_HANDOVER_V2"
)


def _run_ps(script_path, extra_args=None, timeout=180):
    args = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
    if extra_args:
        args.extend(extra_args)
    res = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ORACLE_REPO,
    )
    return {
        "stdout": res.stdout,
        "stderr": res.stderr,
        "code": res.returncode,
    }


def _parse_verify(stdout):
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
            checks.append(
                {
                    "check": parts[0].strip(),
                    "ok": parts[1].strip().lower() == "true",
                    "detail": parts[2].strip(),
                }
            )
    return checks


def _info_xml_settings(path):
    if not os.path.isfile(path):
        return {"exists": False, "path": path}

    tree = ET.parse(path)
    root = tree.getroot()
    strategy = root.find("strategy")
    state = strategy.findtext("State") if strategy is not None else None

    def item_value(name):
        for item in root.findall(".//Item"):
            if item.findtext("Name") == name:
                return item.findtext("Value")

    account = root.find(".//Item[Name='Account']/BusinessObjectInfo")
    symbol = root.find(".//Item[Name='Symbol']/BusinessObjectInfo")

    def bo_info(node):
        if node is None:
            return {"id": "", "connection_id": "", "name": ""}
        return {
            "id": (node.findtext("Id") or "").strip(),
            "connection_id": (node.findtext("ConnectionId") or "").strip(),
            "name": (node.findtext("Name") or "").strip(),
        }

    return {
        "exists": True,
        "path": path,
        "instance_id": strategy.findtext("Id") if strategy is not None else "",
        "state": state,
        "symbol_bound": bool((symbol.findtext("Name") or "").strip()) if symbol is not None else False,
        "account_bound": bool((account.findtext("Name") or "").strip()) if account is not None else False,
        "account": bo_info(account),
        "symbol": bo_info(symbol),
        "enable_live_trading": item_value("Enable Live Trading"),
        "enable_dry_run_mode": item_value("Enable Dry Run Mode"),
        "primary_symbol_label": item_value("Primary Symbol Label"),
    }


def _quantower_process():
    try:
        res = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-Process -Name Starter -ErrorAction SilentlyContinue | "
                "Select-Object Id,StartTime | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return {"running": False, "processes": []}
        import json

        data = json.loads(res.stdout)
        if isinstance(data, dict):
            data = [data]
        return {"running": len(data) > 0, "processes": data}
    except Exception as exc:
        return {"running": False, "error": str(exc), "processes": []}


def _latest_telemetry():
    if not os.path.isdir(TELEMETRY_CSV_ROOT):
        return {"exists": False, "root": TELEMETRY_CSV_ROOT}

    files = [
        f
        for f in os.listdir(TELEMETRY_CSV_ROOT)
        if f.lower().endswith(".csv")
    ]
    if not files:
        return {"exists": False, "root": TELEMETRY_CSV_ROOT}

    latest = max(
        files,
        key=lambda name: os.path.getmtime(os.path.join(TELEMETRY_CSV_ROOT, name)),
    )
    path = os.path.join(TELEMETRY_CSV_ROOT, latest)
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    tail_lines = []
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

    return {
        "exists": True,
        "file": latest,
        "path": path,
        "last_write_utc": mtime.isoformat(),
        "tail": tail_lines,
        "pipeline_active": active,
    }


def oracle_status():
    verify = _run_ps(VERIFY_SCRIPT, ["-InfoXmlPath", INFO_XML])
    dll_hash = ""
    dll_mtime = ""
    if os.path.isfile(STRATEGY_DLL):
        import hashlib

        with open(STRATEGY_DLL, "rb") as handle:
            dll_hash = hashlib.sha256(handle.read()).hexdigest()[:12]
        dll_mtime = datetime.fromtimestamp(
            os.path.getmtime(STRATEGY_DLL), tz=timezone.utc
        ).isoformat()

    info = _info_xml_settings(INFO_XML)
    blockers = []
    if not info.get("symbol_bound"):
        blockers.append("Symbol not bound in info.xml — StM settings required")
    if not info.get("account_bound"):
        blockers.append("Account not bound in info.xml — StM settings required")
    if not _quantower_process().get("running"):
        blockers.append("Quantower Starter not running")

    telemetry = _latest_telemetry()
    if telemetry.get("exists") and not telemetry.get("pipeline_active"):
        blockers.append("Telemetry idle — wire MES replay or start strategy feed")

    return {
        "oracle_repo": ORACLE_REPO,
        "branch": "perf/fix-empty-catch-block-datafeedmanager",
        "deployed_dll": {
            "path": STRATEGY_DLL,
            "sha256_prefix": dll_hash,
            "last_write_utc": dll_mtime,
        },
        "instance": info,
        "quantower": _quantower_process(),
        "telemetry": telemetry,
        "verify": {
            "code": verify["code"],
            "checks": _parse_verify(verify["stdout"]),
            "stderr": verify["stderr"].strip(),
        },
        "blockers": blockers,
        "gates": {
            "g2_dll_deployed": verify["code"] == 0,
            "g3_dry_run_proof": False,
            "g4_dom_l2": False,
            "g5_order_lifecycle": False,
        },
        "next_actions": [
            "GET /ui/screenshot before any Quantower click",
            "Bind Symbol (MES) + demo Account in StM if blockers list binding",
            "Wire MES Market Replay chart to instance",
            "POST /fs/grep for BROKER_SUBMISSION_BLOCKED_DRY_RUN in logs",
            "POST /inbox/write with screenshot + verify evidence",
        ],
    }


def oracle_build_deploy():
    build = subprocess.run(
        [
            "dotnet",
            "build",
            r"OracleV5.Strategy\OracleV5.Strategy.csproj",
            "-c",
            "Release",
            "-a",
            "x64",
        ],
        cwd=ORACLE_REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )
    deploy = _run_ps(DEPLOY_SCRIPT)
    verify = _run_ps(VERIFY_SCRIPT, ["-InfoXmlPath", INFO_XML])
    return {
        "build": {
            "code": build.returncode,
            "stdout_tail": build.stdout.splitlines()[-8:],
            "stderr_tail": build.stderr.splitlines()[-8:],
        },
        "deploy": deploy,
        "verify": {
            "code": verify["code"],
            "checks": _parse_verify(verify["stdout"]),
        },
        "status": oracle_status(),
    }


def codex_handover_index():
    root = CODEX_HANDOVER_ROOT
    if not os.path.isdir(root):
        return {
            "exists": False,
            "path": root,
            "message": "Codex handover folder not found on host",
        }

    files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            files.append(
                {
                    "relative_path": rel.replace("\\", "/"),
                    "size": os.path.getsize(full),
                }
            )
    files.sort(key=lambda item: item["relative_path"])
    return {
        "exists": True,
        "path": root,
        "file_count": len(files),
        "files": files[:200],
        "read_via": 'POST /fs/read {"path":"\\\\\\"...full path..."}',
    }
