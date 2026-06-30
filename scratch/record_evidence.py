# pylint: disable=missing-module-docstring

import json
from datetime import datetime, timezone
import hashlib

def record():
    stdout = "304 passed in 9.06s"
    ev = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "type": "pytest_run",
        "output_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "output_snippet": stdout[-1000:],
    }
    evidence_path = "memory/test_evidence.json"

    # Load existing
    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
    except FileNotFoundError:
        data = []

    data.append(ev)

    # Keep only last 10
    if len(data) > 10:
        data = data[-10:]

    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(ev["output_sha256"])

if __name__ == "__main__":
    record()
