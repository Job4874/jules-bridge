"""CLI entrypoint for Ensure-JulesSecrets.ps1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.jules_env import ensure_persistent_secrets


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Jules secrets persist and ngrok auth is configured.")
    parser.add_argument("--ngrok-authtoken", default="", help="Optional ngrok authtoken to store once.")
    parser.add_argument("--force-ngrok", action="store_true", help="Replace an existing NGROK_AUTHTOKEN.")
    args = parser.parse_args()

    result = ensure_persistent_secrets(
        ngrok_authtoken=args.ngrok_authtoken,
        force_ngrok=args.force_ngrok,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ngrok_configured") else 2


if __name__ == "__main__":
    sys.exit(main())
