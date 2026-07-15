"""Launch Jules Bridge locally and expose it through the reserved ngrok domain."""
import json
import logging
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
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


def main():
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

class TunnelWatchdog:
    def __init__(self, inbox_dir=ROOT / "jules_inbox"):
        self.inbox_dir = inbox_dir
        self.consecutive_failures = 0
        self.reconnect_failures = 0
        self.last_reconnect_utc = None
        self.last_success_utc = datetime.now(timezone.utc)

    def run_loop(self):
        while True:
            time.sleep(60)
            self.check_tunnel()

    def check_tunnel(self):
        try:
            with urllib.request.urlopen(f"https://{NGROK_DOMAIN}/ping", timeout=5) as resp:
                if resp.status == 200:
                    self.consecutive_failures = 0
                    self.reconnect_failures = 0
                    self.last_success_utc = datetime.now(timezone.utc)
                else:
                    self.consecutive_failures += 1
        except OSError:
            self.consecutive_failures += 1

        uptime_s = (datetime.now(timezone.utc) - self.last_success_utc).total_seconds()
        status = "healthy" if self.consecutive_failures == 0 else "reconnecting" if self.consecutive_failures >= 3 else "degraded"

        health_file = self.inbox_dir / "TUNNEL_HEALTH.json"
        health_data = {
            "status": status,
            "last_check_utc": datetime.now(timezone.utc).isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "last_reconnect_utc": self.last_reconnect_utc.isoformat() if self.last_reconnect_utc else None,
            "uptime_s": uptime_s,
        }
        health_file.write_text(json.dumps(health_data, indent=2), encoding="utf-8")

        if self.consecutive_failures >= 3:
            log(f"Watchdog: {self.consecutive_failures} failures. Reconnecting ngrok...")
            try:
                ngrok.kill()
                time.sleep(1)
                ngrok.connect(5000, domain=NGROK_DOMAIN)
                self.last_reconnect_utc = datetime.now(timezone.utc)
                self.consecutive_failures = 0
            except Exception as e:
                self.reconnect_failures += 1
                log(f"Watchdog reconnect failed: {e}")

            if self.reconnect_failures == 3:
                self.escalate_offline()

    def escalate_offline(self):
        log("FATAL: Tunnel cannot self-heal. Triggering Git offline escalation.")
        blocker_file = self.inbox_dir / "TUNNEL_BLOCKER.md"
        blocker_file.write_text("NGROK TUNNEL IS DEAD AND CANNOT SELF-HEAL.", encoding="utf-8")
        response_file = self.inbox_dir / "JULES_RESPONSE.md"
        with response_file.open("a", encoding="utf-8") as f:
            f.write("\n[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.\n")

        try:
            subprocess.run(["git", "add", str(blocker_file), str(response_file), str(self.inbox_dir / "TUNNEL_HEALTH.json")], cwd=str(ROOT), check=True)
            subprocess.run(["git", "commit", "-m", "[TUNNEL_DEAD] Ngrok tunnel cannot self-heal"], cwd=str(ROOT), check=True)
            subprocess.run(["git", "push"], cwd=str(ROOT), check=True)
        except subprocess.CalledProcessError as e:
            log(f"Failed to push offline escalation: {e}")

if __name__ == "__main__":
    main()

    watchdog = TunnelWatchdog()
    threading.Thread(target=watchdog.run_loop, daemon=True).start()

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
