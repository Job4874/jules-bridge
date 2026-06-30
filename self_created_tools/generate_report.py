import os
import json
import time
from datetime import datetime, timezone
import subprocess
import argparse
from modules.vm_manager import detect_resource_pressure
from modules.akc_module import check_akc_readiness
from modules.retrospective_module import load_test_evidence
import notify_email

def get_git_status():
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        last_commit = subprocess.check_output(["git", "log", "-1", "--format=%h — %s"], text=True).strip()
        return branch, last_commit
    except:
        return "unknown", "unknown"

def generate_report(work_completed, files_changed, validation_evidence, screenshots_evidence, commit_push_status, blockers_needs, next_30_minutes):
    branch, last_commit = get_git_status()
    pressure = detect_resource_pressure()
    akc = check_akc_readiness()
    evidence = load_test_evidence("memory")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report = f"# [JULES-UPDATE] Progress Report - {timestamp}\n\n"

    report += "## Snapshot\n"
    report += f"| Field | Value |\n"
    report += f"|---|---|\n"
    report += f"| **Repo** | {os.getcwd()} |\n"
    report += f"| **Branch** | {branch} |\n"
    report += f"| **Last commit** | {last_commit} |\n"
    if evidence:
        report += f"| **Tests** | {evidence.test_count} passed (sha256:{evidence.output_hash[:12]}) |\n"
    else:
        report += f"| **Tests** | No recent evidence found |\n"
    report += "\n"

    report += "## HRM Checkpoint\n"
    report += f"- AKC Readiness: {akc.get('status', 'unknown')}\n"
    report += f"- Operating Rules: {akc.get('operating_rule_count', 0)}\n"
    report += "\n"

    report += "## Work Completed\n"
    report += work_completed + "\n\n"

    report += "## Files Changed\n"
    report += files_changed + "\n\n"

    report += "## Validation / Evidence\n"
    report += validation_evidence + "\n\n"

    report += "## Screenshots/evidence\n"
    report += screenshots_evidence + "\n\n"

    report += "## Commit / Push Status\n"
    report += commit_push_status + "\n\n"

    report += "## VM / Compute Status\n"
    report += f"- CPU: {pressure.get('cpu_percent')}%" + (" (CROSSING THRESHOLD)" if pressure.get('maxed_out') and 'cpu' in str(pressure.get('reasons')) else "") + "\n"
    report += f"- Memory: {pressure.get('memory_percent')}%" + (" (CROSSING THRESHOLD)" if pressure.get('maxed_out') and 'memory' in str(pressure.get('reasons')) else "") + "\n"
    report += f"- Maxed Out: {pressure.get('maxed_out')}\n"
    report += "- Cloud Offload: None in this session\n"
    report += "\n"

    report += "## Blockers / Needs\n"
    report += blockers_needs + "\n\n"

    report += "## Next 30 Minutes\n"
    report += next_30_minutes + "\n"

    return report

def main():
    parser = argparse.ArgumentParser(description="Generate and optionally send a Jules Progress Report")
    parser.add_argument("--work", required=True, help="Work completed")
    parser.add_argument("--files", required=True, help="Files changed")
    parser.add_argument("--validation", required=True, help="Validation / Evidence")
    parser.add_argument("--screenshots", required=True, help="Screenshots/evidence")
    parser.add_argument("--commit", required=True, help="Commit / Push Status")
    parser.add_argument("--blockers", required=True, help="Blockers / Needs")
    parser.add_argument("--next", required=True, help="Next 30 Minutes")
    parser.add_argument("--send", action="store_true", help="Send the report via email")
    parser.add_argument("--attachments", nargs="*", help="List of file paths to attach")

    args = parser.parse_args()

    report_text = generate_report(
        args.work,
        args.files,
        args.validation,
        args.screenshots,
        args.commit,
        args.blockers,
        args.next
    )

    print(report_text)

    if args.send:
        subject = f"[JULES-UPDATE] Progress Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        try:
            notify_email.send_email(subject, report_text, attachments=args.attachments)
            print("\n[+] Report sent successfully.")
        except Exception as e:
            print(f"\n[-] Failed to send report: {e}")
            # Fallback to writing to JULES_RESPONSE.md
            with open("jules_inbox/JULES_RESPONSE.md", "a", encoding="utf-8") as f:
                f.write("\n\n" + report_text)
            print("[*] Report appended to jules_inbox/JULES_RESPONSE.md instead.")

if __name__ == "__main__":
    main()
