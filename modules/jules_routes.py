"""Jules Orchestrator routes for the Jules Bridge.

This module contains the Flask Blueprint for all /jules/* endpoints.
"""
from __future__ import annotations

from flask import Blueprint, jsonify
import modules
from .http_utils import (
    route_errors,
    json_payload,
    string_field,
    int_field,
    bool_field,
    BridgeHTTPError,
)

jules_bp = Blueprint("jules", __name__)

@jules_bp.route("/dispatch", methods=["POST"])
@route_errors
def jules_dispatch():
    """POST /jules/dispatch - Build dry-run Jules worker packets.

    Body (JSON):
        content/data       (str, optional): Raw pasted Jules task dump
        source_path/path   (str, optional): File path containing a task dump
        max_instances      (int, optional, default=4): Max packets to select
        include_statuses   (str|list, optional): Statuses to include
        write_packets      (bool, optional, default=false): Write packet files
        output_dir         (str, optional): Packet destination directory
        repo_path          (str, optional): Repo workers should launch from

    Returns a dispatch preview. It never launches remote Jules sessions.
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.build_dispatch(
        content=content,
        source_path=source_path,
        max_instances=int_field(data, "max_instances", default=4, min_value=1, max_value=50),
        include_statuses=include_statuses,
        write_packets=bool_field(data, "write_packets", default=False),
        output_dir=string_field(data, "output_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/launch", methods=["POST"])
@route_errors
def jules_launch():
    """POST /jules/launch - Launch prepared Jules worker packets.

    Body (JSON):
        packet_dir    (str, optional): Directory containing JT-*.md packets
        packet_files  (list[str], optional): Explicit packet paths
        repo_path     (str, optional): Working directory for `jules new`
        limit         (int, optional, default=0): Max packets; 0 means all
        dry_run       (bool, optional, default=true): False starts sessions
        timeout_s     (int, optional, default=120): Per-packet timeout
        jules_command (str, optional, default="jules"): CLI path/name
        write_state   (bool, optional, default=true): Persist launch state JSON
        state_path    (str, optional): Explicit state file path
        skip_launched (bool, optional, default=false): Skip packets already launched in state
        force_packet_files (list[str], optional): Explicit packet paths to relaunch
        preserve_existing_session_ids (bool, optional, default=false): Keep older session ids on duplicate launches
    """
    data = json_payload()
    packet_files = data.get("packet_files")
    if packet_files is not None:
        if not isinstance(packet_files, list) or not all(isinstance(item, str) for item in packet_files):
            raise BridgeHTTPError(400, "Invalid input", details="packet_files must be a list of strings")
    force_packet_files = data.get("force_packet_files")
    if force_packet_files is not None:
        if not isinstance(force_packet_files, list) or not all(isinstance(item, str) for item in force_packet_files):
            raise BridgeHTTPError(400, "Invalid input", details="force_packet_files must be a list of strings")

    result = modules.launch_packets(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        packet_files=packet_files,
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        limit=int_field(data, "limit", default=0, min_value=0, max_value=100),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_state=bool_field(data, "write_state", default=True),
        state_path=string_field(data, "state_path", default="", allow_empty=True, control_safe=True),
        skip_launched=bool_field(data, "skip_launched", default=False),
        force_packet_files=force_packet_files,
        preserve_existing_session_ids=bool_field(data, "preserve_existing_session_ids", default=False),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/sessions", methods=["POST"])
@route_errors
def jules_sessions():
    """POST /jules/sessions - List remote Jules sessions.

    Body (JSON):
        dry_run       (bool, optional, default=true): False invokes the CLI
        timeout_s     (int, optional, default=30): CLI timeout
        jules_command (str, optional, default="jules"): CLI path/name
    """
    data = json_payload()
    result = modules.list_remote_sessions(
        jules_command=string_field(data, "jules_command", default="jules"),
        timeout_s=int_field(data, "timeout_s", default=30, min_value=1, max_value=300),
        dry_run=bool_field(data, "dry_run", default=True),
    )
    return jsonify(dict(result))


@jules_bp.route("/preflight", methods=["POST"])
@route_errors
def jules_preflight_route():
    """POST /jules/preflight - Diagnose Jules CLI readiness.

    Body (JSON):
        jules_command (str, optional, default="jules"): CLI path/name
        timeout_s     (int, optional, default=8): Probe timeout
        check_remote  (bool, optional, default=true): Run remote list probe
        write_state   (bool, optional, default=true): Persist preflight JSON
        state_path    (str, optional): Explicit state file path
    """
    data = json_payload()
    result = modules.jules_preflight(
        jules_command=string_field(data, "jules_command", default="jules"),
        timeout_s=int_field(data, "timeout_s", default=8, min_value=1, max_value=300),
        check_remote=bool_field(data, "check_remote", default=True),
        write_state=bool_field(data, "write_state", default=True),
        state_path=string_field(data, "state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/pull", methods=["POST"])
@route_errors
def jules_pull():
    """POST /jules/pull - Pull one remote Jules session.

    Body (JSON):
        session_id    (str, required): Remote Jules session id
        repo_path     (str, optional): Working directory for pull
        output_dir    (str, optional): Directory for persisted pull JSON
        dry_run       (bool, optional, default=true): False invokes the CLI
        timeout_s     (int, optional, default=120): CLI timeout
        jules_command (str, optional, default="jules"): CLI path/name
        write_result  (bool, optional, default=true): Persist pull result JSON
    """
    data = json_payload()
    result = modules.pull_remote_session(
        session_id=string_field(data, "session_id"),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        output_dir=string_field(data, "output_dir", default="", allow_empty=True, control_safe=True),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_result=bool_field(data, "write_result", default=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/cot", methods=["POST"])
@route_errors
def jules_cot():
    """POST /jules/cot - Build a completion-of-task ledger.

    Body (JSON):
        packet_dir         (str, optional): Dispatch packet directory
        launch_state_path  (str, optional): Explicit launch state JSON path
        report_dir         (str, optional): Completion report or pull JSON dir
        output_path        (str, optional): Markdown ledger destination
        write_ledger       (bool, optional, default=true): Persist ledger files
    """
    data = json_payload()
    result = modules.build_cot_ledger(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        launch_state_path=string_field(data, "launch_state_path", default="", allow_empty=True, control_safe=True),
        report_dir=string_field(data, "report_dir", default="", allow_empty=True, control_safe=True),
        output_path=string_field(data, "output_path", default="", allow_empty=True, control_safe=True),
        write_ledger=bool_field(data, "write_ledger", default=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/cycle", methods=["POST"])
@route_errors
def jules_cycle():
    """POST /jules/cycle - Run one Jules communication cycle.

    Body (JSON):
        content/data          (str, optional): Raw pasted Jules task dump
        source_path/path      (str, optional): File path containing task dump
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers should launch from
        max_instances         (int, optional, default=4): Max packets
        include_statuses      (str|list, optional): Statuses to include
        launch                (bool, optional, default=false): Request launch
        launch_limit          (int, optional, default=0): Max launches
        pull                  (bool, optional, default=false): Pull session ids
        session_ids           (list[str], optional): Explicit session ids
        dry_run               (bool, optional, default=true): False enables live CLI
        check_remote          (bool, optional, default=true): Probe remote sessions
        require_remote_ready  (bool, optional, default=true): Gate live launch/pull
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        write_state           (bool, optional, default=true): Persist cycle JSON
        cycle_state_path      (str, optional): Explicit cycle state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    session_ids = data.get("session_ids")
    if session_ids is not None:
        if not isinstance(session_ids, list) or not all(isinstance(item, str) for item in session_ids):
            raise BridgeHTTPError(400, "Invalid input", details="session_ids must be a list of strings")

    result = modules.run_jules_cycle(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=4, min_value=1, max_value=50),
        include_statuses=include_statuses,
        write_packets=bool_field(data, "write_packets", default=True),
        launch=bool_field(data, "launch", default=False),
        launch_limit=int_field(data, "launch_limit", default=0, min_value=0, max_value=100),
        pull=bool_field(data, "pull", default=False),
        session_ids=session_ids,
        dry_run=bool_field(data, "dry_run", default=True),
        check_remote=bool_field(data, "check_remote", default=True),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        write_state=bool_field(data, "write_state", default=True),
        cycle_state_path=string_field(data, "cycle_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/watch", methods=["POST"])
@route_errors
def jules_watch():
    """POST /jules/watch - Watch launched Jules sessions until COT progresses.

    Body (JSON):
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers launched from
        max_wait_s            (int, optional, default=300): Watch time budget
        poll_interval_s       (int, optional, default=30): Seconds between polls
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        dry_run               (bool, optional, default=true): False enables live pulls
        require_remote_ready  (bool, optional, default=true): Gate live pull
        write_state           (bool, optional, default=true): Persist watch JSON
        watch_state_path      (str, optional): Explicit watch state path
    """
    data = json_payload()
    result = modules.run_jules_watch(
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_wait_s=int_field(data, "max_wait_s", default=300, min_value=0, max_value=7200),
        poll_interval_s=int_field(data, "poll_interval_s", default=30, min_value=1, max_value=600),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        dry_run=bool_field(data, "dry_run", default=True),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        watch_state_path=string_field(data, "watch_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/fleet", methods=["POST"])
@route_errors
def jules_fleet():
    """POST /jules/fleet - Maintain a bounded Jules worker fleet.

    Body (JSON):
        content/data          (str, optional): Raw pasted Jules task dump
        source_path/path      (str, optional): File path containing task dump
        packet_dir            (str, optional): Packet/state directory
        repo_path             (str, optional): Repo workers should launch from
        max_instances         (int, optional, default=12): Queue size to maintain
        max_concurrent        (int, optional, default=6): Max active remote sessions
        launch_batch_size     (int, optional, default=2): Max launches this cycle
        include_statuses      (str|list, optional): Statuses to include
        dry_run               (bool, optional, default=true): False enables live CLI
        timeout_s             (int, optional, default=120): CLI timeout
        jules_command         (str, optional, default="jules"): CLI path/name
        require_remote_ready  (bool, optional, default=true): Gate live launch/pull
        write_state           (bool, optional, default=true): Persist fleet JSON
        fleet_state_path      (str, optional): Explicit fleet state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.run_jules_fleet(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=12, min_value=1, max_value=100),
        max_concurrent=int_field(data, "max_concurrent", default=6, min_value=0, max_value=50),
        launch_batch_size=int_field(data, "launch_batch_size", default=2, min_value=0, max_value=50),
        include_statuses=include_statuses,
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        fleet_state_path=string_field(data, "fleet_state_path", default="", allow_empty=True, control_safe=True),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/fleet-watch", methods=["POST"])
@route_errors
def jules_fleet_watch():
    """POST /jules/fleet-watch - Scale, pull, and watch COT in one loop.

    Body (JSON):
        content/data             (str, optional): Raw pasted Jules task dump
        source_path/path         (str, optional): File path containing task dump
        packet_dir               (str, optional): Packet/state directory
        repo_path                (str, optional): Repo workers should launch from
        max_instances            (int, optional, default=12): Queue size to maintain
        max_concurrent           (int, optional, default=6): Max active remote sessions
        launch_batch_size        (int, optional, default=2): Max launches per loop
        include_statuses         (str|list, optional): Statuses to include
        max_wait_s               (int, optional, default=900): Watch time budget
        poll_interval_s          (int, optional, default=30): Seconds between loops
        dry_run                  (bool, optional, default=true): False enables live CLI
        timeout_s                (int, optional, default=120): CLI timeout
        jules_command            (str, optional, default="jules"): CLI path/name
        require_remote_ready     (bool, optional, default=true): Gate live launch/pull
        write_state              (bool, optional, default=true): Persist state JSON
        fleet_watch_state_path   (str, optional): Explicit state path
    """
    data = json_payload()
    content = ""
    if "content" in data:
        content = string_field(data, "content", allow_empty=True)
    elif "data" in data:
        content = string_field(data, "data", allow_empty=True)

    source_path = ""
    if "source_path" in data:
        source_path = string_field(data, "source_path", allow_empty=True, control_safe=True)
    elif "path" in data:
        source_path = string_field(data, "path", allow_empty=True, control_safe=True)

    include_statuses = data.get("include_statuses", "")
    if include_statuses and not isinstance(include_statuses, (str, list, tuple)):
        raise BridgeHTTPError(400, "Invalid input", details="include_statuses must be a string or list")

    result = modules.run_jules_fleet_watch(
        content=content,
        source_path=source_path,
        packet_dir=string_field(data, "packet_dir", default="", allow_empty=True, control_safe=True),
        repo_path=string_field(data, "repo_path", default="", allow_empty=True, control_safe=True),
        max_instances=int_field(data, "max_instances", default=12, min_value=1, max_value=100),
        max_concurrent=int_field(data, "max_concurrent", default=6, min_value=0, max_value=50),
        launch_batch_size=int_field(data, "launch_batch_size", default=2, min_value=0, max_value=50),
        include_statuses=include_statuses,
        max_wait_s=int_field(data, "max_wait_s", default=900, min_value=0, max_value=14400),
        poll_interval_s=int_field(data, "poll_interval_s", default=30, min_value=1, max_value=600),
        dry_run=bool_field(data, "dry_run", default=True),
        timeout_s=int_field(data, "timeout_s", default=120, min_value=1, max_value=3600),
        jules_command=string_field(data, "jules_command", default="jules"),
        require_remote_ready=bool_field(data, "require_remote_ready", default=True),
        write_state=bool_field(data, "write_state", default=True),
        fleet_watch_state_path=string_field(
            data,
            "fleet_watch_state_path",
            default="",
            allow_empty=True,
            control_safe=True,
        ),
    )
    status = 400 if result.get("error") else 200
    return jsonify(dict(result)), status


@jules_bp.route("/api/sources", methods=["POST"])
@route_errors
def jules_api_sources():
    """POST /jules/api/sources - List Jules REST API sources."""
    from modules import jules_api  # pylint: disable=import-outside-toplevel

    data = json_payload()
    result = jules_api.list_sources(timeout_s=int_field(data, "timeout_s", default=30, min_value=1, max_value=120))
    status = 200 if result.get("ok") else 502
    return jsonify(dict(result)), status


@jules_bp.route("/api/sessions", methods=["POST"])
@route_errors
def jules_api_create_session():
    """POST /jules/api/sessions - Create a Jules REST API session."""
    from modules import jules_api  # pylint: disable=import-outside-toplevel

    data = json_payload()
    result = jules_api.create_session(
        prompt=string_field(data, "prompt"),
        source=string_field(data, "source", default="", allow_empty=True),
        title=string_field(data, "title", default="", allow_empty=True),
        starting_branch=string_field(data, "starting_branch", default="main"),
        automation_mode=string_field(data, "automation_mode", default="", allow_empty=True),
        require_plan_approval=bool_field(data, "require_plan_approval", default=False),
        timeout_s=int_field(data, "timeout_s", default=60, min_value=1, max_value=300),
    )
    status = 200 if result.get("ok") else 502
    return jsonify(dict(result)), status


@jules_bp.route("/api/sessions/list", methods=["POST"])
@route_errors
def jules_api_list_sessions():
    """POST /jules/api/sessions/list - List Jules REST API sessions."""
    from modules import jules_api  # pylint: disable=import-outside-toplevel

    data = json_payload()
    result = jules_api.list_sessions(
        page_size=int_field(data, "page_size", default=30, min_value=1, max_value=100),
        page_token=string_field(data, "page_token", default="", allow_empty=True),
        timeout_s=int_field(data, "timeout_s", default=30, min_value=1, max_value=120),
    )
    status = 200 if result.get("ok") else 502
    return jsonify(dict(result)), status
