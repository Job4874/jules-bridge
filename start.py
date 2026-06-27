"""Launch Jules Bridge locally and expose it through the reserved ngrok domain."""
import atexit
import logging
import subprocess
import sys
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pyngrok import ngrok
from pyngrok.exception import PyngrokError

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bridge.log"
NGROK_DOMAIN = "parade-marrow-pulp.ngrok-free.dev"


class _BridgeState:
    """Mutable launcher state shared by startup and shutdown hooks."""

    flask_process: subprocess.Popen | None = None


STATE = _BridgeState()


def configure_logging() -> logging.Logger:
    """Configure rotating file and stdout logging for the launcher."""
    logger = logging.getLogger("jules_bridge_start")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=10_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


LOGGER = configure_logging()


def log(message: str) -> None:
    """Write an INFO log line through the launcher logger."""
    LOGGER.info(message)


def ping_local() -> bool:
    """Return True when the local bridge responds on /ping."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:5000/ping", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


def stop_flask() -> None:
    """Terminate the bridge subprocess if it is still running."""
    if STATE.flask_process and STATE.flask_process.poll() is None:
        STATE.flask_process.terminate()
        try:
            STATE.flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            STATE.flask_process.kill()


def start_flask() -> subprocess.Popen:
    """Start bridge.py and return the subprocess handle."""
    STATE.flask_process = subprocess.Popen(
        [sys.executable, str(ROOT / "bridge.py")],
        cwd=str(ROOT),
    )
    return STATE.flask_process


atexit.register(stop_flask)

log("Starting Jules Bridge locally...")
start_flask()

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
except PyngrokError as exc:
    if ping_local():
        log(f"ngrok connect failed ({exc}) but local bridge is UP.")
        log("Try reopening tunnel or use: http://127.0.0.1:5000")
        log(f"Expected public URL: https://{NGROK_DOMAIN}")
    else:
        log(f"FATAL: ngrok and local bridge both unavailable: {exc}")
        stop_flask()
        sys.exit(1)

log("Keeping process alive. Do not close this window.")

try:
    while True:
        if STATE.flask_process and STATE.flask_process.poll() is not None:
            log(f"ERROR: bridge.py exited with code {STATE.flask_process.returncode}")
            sys.exit(STATE.flask_process.returncode or 1)
        time.sleep(2)
except KeyboardInterrupt:
    log("Shutting down...")
    stop_flask()
