import os

with open('modules/jules_orchestrator.py', 'w') as f:
    f.write("from .jules import *\n")
    f.write("from .jules.parser import *\n")
    f.write("from .jules.cli import *\n")
    f.write("from .jules.dispatch import *\n")
    f.write("from .jules.reporting import *\n")
    f.write("from .jules.orchestrator import *\n")
    f.write("from .jules.cli import _run_cli_command, _auth_indicators, _candidate_jules_commands\n")
    f.write("from .jules.utils import _coerce_text, _read_json_file, _safe_filename, _merge_unique, _ps_quote, _terminate_process_tree\n")
    f.write("from .jules.parser import _status_filter, _count_statuses, _select_tasks, _dedupe_tasks, _sha256, _packet_id_from_path, _extract_packet_ids, _heading_type, _nearest_prefix_status, _nearest_suffix_status, _extract_file_and_issue, _extract_prefixed, _title_for, _compact_lines\n")
    f.write("from .jules.cli import _state_path_for, _extract_session_ids, _resolve_cli_command, _append_candidate, _preferred_jules_command, _safe_child_count, _preflight_blocker, _cli_output_has_error, _already_launched_packet_keys, _remote_status_from_line, _remote_last_active_seconds, _active_remote_session_count, _watch_terminal_status, _completed_session_ids, _session_status_rows, _count_remote_statuses\n")
    f.write("from .jules.dispatch import _packet_text, _launch_command, _write_dispatch_files, _clear_previous_dispatch, _resolve_packet_files, _packet_files_from_index, _launch_succeeded, _stored_launch_succeeded, _merge_launch_results, _merge_launch_session_ids, _results_by_packet, _not_launched_result, _dispatch_index, _launch_script\n")
    f.write("from .jules.reporting import _cot_rows_from_state, _collect_cot_reports, _read_report_content, _matching_reports, _classify_cot_status, _looks_complete, _looks_blocked, _looks_pulled_output, _count_row_statuses, _cot_ledger_markdown\n")
    f.write("from .jules.orchestrator import _cycle_session_ids, _launched_session_ids, _failed_remote_packet_files, _stale_unknown_remote_packet_files, _plan_awaiting_remote_packet_files, _successful_pull_session_ids\n")
