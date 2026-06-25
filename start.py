import atexit
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pyngrok import ngrok

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bridge.log"
NGROK_DOMAIN = "parade-marrow-pulp.ngrok-free.dev"


def log(message):
    line = f"{datetime.now(timezone.utc).isoformat()} {message}"
    print(message, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def ping_local():
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:5000/ping", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


flask_process = None


def stop_flask():
    global flask_process
    if flask_process and flask_process.poll() is None:
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            flask_process.kill()


atexit.register(stop_flask)

log("Starting Jules Bridge locally...")
flask_process = subprocess.Popen(
    [sys.executable, str(ROOT / "bridge.py")],
    cwd=str(ROOT),
)

for _ in range(20):
    if ping_local():
        break
    time.sleep(0.5)
else:
    log("ERROR: bridge.py did not respond on port 5000")
    stop_flask()
    sys.exit(1)

log("Flask bridge online at http://127.0.0.1:5000")

log("Opening ngrok tunnel...")
try:
    public_url = ngrok.connect(5000, domain=NGROK_DOMAIN)
    log("========================================")
    log(f"NGROK URL: {public_url.public_url}")
    log("========================================")
except Exception as exc:
    if ping_local():
        log(f"ngrok connect failed ({exc}) but local bridge is UP.")
        log(f"Try reopening tunnel or use: http://127.0.0.1:5000")
        log(f"Expected public URL: https://{NGROK_DOMAIN}")
    else:
        log(f"FATAL: ngrok and local bridge both unavailable: {exc}")
        stop_flask()
        sys.exit(1)

log("Keeping process alive. Do not close this window.")

try:
    while True:
        if flask_process.poll() is not None:
            log(f"ERROR: bridge.py exited with code {flask_process.returncode}")
            sys.exit(flask_process.returncode or 1)
        time.sleep(2)
except KeyboardInterrupt:
    log("Shutting down...")
    stop_flask()
