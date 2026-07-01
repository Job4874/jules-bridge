"""CLI for ghost lock/unlock — avoids PowerShell quoting issues with passwords."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import modules.ghost_state as ghost_state  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ghost state lock/unlock")
    parser.add_argument("action", choices=("lock", "unlock", "status"))
    parser.add_argument("--password", default="", help="Operator password")
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()

    if args.action == "status":
        state = ghost_state.load_ghost_state()
        print("locked" if state.get("locked") else "unlocked")
        return 0

    if not args.password.strip():
        print("error: --password required", file=sys.stderr)
        return 1

    if args.action == "lock":
        result = ghost_state.lock_ghost(args.password, repo_root=args.repo_root)
    else:
        result = ghost_state.unlock_ghost(args.password, repo_root=args.repo_root)

    print(result.get("status", "error"))
    return 0 if result.get("status") in ("locked", "unlocked") else 1


if __name__ == "__main__":
    raise SystemExit(main())
