from __future__ import annotations
from .models import *
from .utils import *
from .parser import *
from .cli import *
from .dispatch import *

def build_cot_ledger(
    packet_dir: str = "",
    launch_state_path: str = "",
    report_dir: str = "",
    output_path: str = "",
    write_ledger: bool = True,
) -> JulesCotResult:
    """Build a completion-of-task ledger from Jules launch/pull artifacts.

    Args:
        packet_dir: Directory containing packets and launch state.
        launch_state_path: Explicit `JULES_LAUNCH_STATE.json` path.
        report_dir: Directory containing completion reports or pull JSON files.
        output_path: Markdown ledger destination.
        write_ledger: Persist markdown and JSON ledger artifacts.

    Returns:
        JulesCotResult. Never raises.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        base_dir = Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR
        state_path = Path(launch_state_path) if launch_state_path else base_dir / _DEFAULT_STATE_FILE
        state = _read_json_file(state_path)
        rows = _cot_rows_from_state(state, base_dir)
        if not rows:
            return JulesCotResult(
                error="no launch state or packet files found",
                generated_at_utc=generated_at,
                packet_dir=str(base_dir),
                launch_state_path=str(state_path),
                selected_count=0,
                rows=[],
            )
        reports = _collect_cot_reports(base_dir=base_dir, report_dir=report_dir)
        for row in rows:
            matches = _matching_reports(row, reports)
            row["report_files"] = [match["path"] for match in matches]
            row["cot_status"] = _classify_cot_status(row, matches)
        status_counts = _count_row_statuses(rows)
        completed_count = sum(status_counts.get(status, 0) for status in _COMPLETED_COT_STATUSES)
        blocked_count = sum(count for status, count in status_counts.items() if "blocked" in status)
        pending_count = len(rows) - completed_count - blocked_count
        payload = JulesCotResult(
            generated_at_utc=generated_at,
            packet_dir=str(base_dir),
            launch_state_path=str(state_path),
            report_dir=str(Path(report_dir)) if report_dir else "",
            selected_count=len(rows),
            completed_count=completed_count,
            blocked_count=blocked_count,
            pending_count=max(0, pending_count),
            all_complete=len(rows) > 0 and completed_count == len(rows),
            status_counts=status_counts,
            rows=rows,
            ledger_path="",
            ledger_json_path="",
            note="COT means completion-of-task evidence summaries, not private chain-of-thought.",
        )
        if write_ledger:
            ledger_path = Path(output_path) if output_path else base_dir / _DEFAULT_COT_LEDGER
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            payload["ledger_path"] = str(ledger_path)
            payload["ledger_json_path"] = str(ledger_path.with_suffix(".json"))
            ledger_path.write_text(_cot_ledger_markdown(payload), encoding="utf-8")
            ledger_path.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # noqa: BLE001
        return JulesCotResult(
            error=str(exc),
            generated_at_utc=generated_at,
            packet_dir=str(Path(packet_dir) if packet_dir else _DEFAULT_OUTPUT_DIR),
            selected_count=0,
            rows=[],
        )


def _cot_rows_from_state(state: dict, base_dir: Path) -> list[dict]:
    rows: list[dict] = []
    state_results = state.get("results") if isinstance(state, dict) else []
    if isinstance(state_results, list) and state_results:
        for item in state_results:
            if not isinstance(item, dict):
                continue
            packet = str(item.get("packet", ""))
            rows.append({
                "packet": packet,
                "packet_id": _packet_id_from_path(packet),
                "launch_status": item.get("status", "unknown"),
                "session_ids": [str(value) for value in item.get("session_ids", [])],
                "timed_out": bool(item.get("timed_out")),
                "exit_code": item.get("exit_code"),
                "cot_status": "unknown",
                "report_files": [],
            })
    if rows:
        return rows
    return [
        {
            "packet": str(packet),
            "packet_id": _packet_id_from_path(str(packet)),
            "launch_status": "not_launched",
            "session_ids": [],
            "timed_out": False,
            "exit_code": None,
            "cot_status": "not_launched",
            "report_files": [],
        }
        for packet in _resolve_packet_files(packet_dir=str(base_dir))
    ]


def _collect_cot_reports(base_dir: Path, report_dir: str = "") -> list[dict]:
    roots = []
    if report_dir:
        roots.append(Path(report_dir))
    else:
        roots.extend([base_dir / _DEFAULT_COT_DIR, base_dir / _DEFAULT_PULL_DIR])
    reports: list[dict] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(list(root.glob("*.md")) + list(root.glob("*.json"))):
            content = _read_report_content(path)
            searchable = f"{path.name}\n{content}"
            reports.append({
                "path": str(path),
                "content": content,
                "session_ids": _extract_session_ids(searchable),
                "packet_ids": _extract_packet_ids(searchable),
            })
    return reports


def _read_report_content(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() != ".json":
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    parts = [
        f"status: {payload.get('status', '')}",
        f"exit_code: {payload.get('exit_code', '')}",
        str(payload.get("stdout", "")),
        str(payload.get("stderr", "")),
        str(payload.get("note", "")),
        " ".join(str(value) for value in payload.get("session_ids", []) or []),
    ]
    return "\n".join(part for part in parts if part)


def _read_report_content(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() != ".json":
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    parts = [
        f"status: {payload.get('status', '')}",
        f"exit_code: {payload.get('exit_code', '')}",
        str(payload.get("stdout", "")),
        str(payload.get("stderr", "")),
        str(payload.get("note", "")),
        " ".join(str(value) for value in payload.get("session_ids", []) or []),
    ]
    return "\n".join(part for part in parts if part)


def _matching_reports(row: dict, reports: list[dict]) -> list[dict]:
    packet_id = str(row.get("packet_id", ""))
    session_ids = {str(value) for value in row.get("session_ids", []) if str(value)}
    matches: list[dict] = []
    for report in reports:
        report_packet_ids = set(report.get("packet_ids", []))
        report_session_ids = set(report.get("session_ids", []))
        if packet_id and packet_id in report_packet_ids:
            matches.append(report)
            continue
        if session_ids and session_ids.intersection(report_session_ids):
            matches.append(report)
    return matches


def _classify_cot_status(row: dict, reports: list[dict]) -> str:
    combined = "\n".join(report.get("content", "") for report in reports)
    if reports:
        if _looks_blocked(combined):
            return "blocked_reported"
        if _looks_complete(combined):
            return "completed_reported"
        if _looks_pulled_output(combined):
            return "pulled_output_reported"
        return "report_found_needs_review"
    launch_status = str(row.get("launch_status") or "unknown")
    if launch_status in ("dry_run", "not_launched"):
        return "not_launched"
    if launch_status in ("timeout", "failed", "error"):
        return f"launch_{launch_status}"
    if row.get("session_ids"):
        return "launched_pending_cot"
    if launch_status == "launched":
        return "launched_missing_session_id"
    return "pending_launch"


def _looks_complete(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "completion report" in lower
        or ("what changed" in lower and "verification" in lower)
        or ("files touched" in lower and "verification performed" in lower)
    )


def _looks_blocked(text: str) -> bool:
    lower = (text or "").lower()
    return "blocked" in lower and ("next action" in lower or "blocker" in lower)


def _looks_pulled_output(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "status: pulled" in lower
        and "exit_code: 0" in lower
        and "diff --git " in lower
        and "--- a/" in lower
        and "+++ b/" in lower
    )


def _count_row_statuses(rows: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("cot_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _cot_ledger_markdown(payload: JulesCotResult) -> str:
    lines = [
        "# Jules COT Ledger",
        "",
        f"- generated_at_utc: {payload.get('generated_at_utc', '')}",
        f"- packet_dir: {payload.get('packet_dir', '')}",
        f"- launch_state_path: {payload.get('launch_state_path', '')}",
        f"- selected_count: {payload.get('selected_count', 0)}",
        f"- completed_count: {payload.get('completed_count', 0)}",
        f"- blocked_count: {payload.get('blocked_count', 0)}",
        f"- pending_count: {payload.get('pending_count', 0)}",
        f"- all_complete: {payload.get('all_complete', False)}",
        "",
        "| packet_id | launch_status | session_ids | cot_status | reports |",
        "|---|---|---|---|---|",
    ]
    for row in payload.get("rows", []):
        reports = "<br>".join(Path(path).name for path in row.get("report_files", []))
        lines.append(
            "| {packet_id} | {launch_status} | {session_ids} | {cot_status} | {reports} |".format(
                packet_id=row.get("packet_id", ""),
                launch_status=row.get("launch_status", ""),
                session_ids=", ".join(row.get("session_ids", [])),
                cot_status=row.get("cot_status", ""),
                reports=reports,
            )
        )
    lines.extend([
        "",
        "COT means completion-of-task evidence summaries, not private chain-of-thought.",
        "",
    ])
    return "\n".join(lines)
