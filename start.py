"""Launch Jules Bridge locally and expose it through the reserved ngrok domain."""
import json
import logging
import os
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

from notify_email import load_env

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bridge.log"
NGROK_DOMAIN = "parade-marrow-pulp.ngrok-free.dev"
_NGROK_AUTH_ERROR_MARKERS = ("ERR_NGROK_4018", "not authenticated", "authentication failed")


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


def _ngrok_auth_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(marker.lower() in text.lower() for marker in _NGROK_AUTH_ERROR_MARKERS)


def configure_ngrok_auth() -> bool:
    """Load ngrok authtoken from environment or .env. Returns True when configured."""
    load_env()
    token = os.environ.get("NGROK_AUTHTOKEN", "").strip()
    if not token:
        return False
    ngrok.set_auth_token(token)
    return True


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


def connect_ngrok_tunnel() -> str | None:
    """Open the reserved ngrok tunnel when auth is configured."""
    if not configure_ngrok_auth():
        log("Ngrok authtoken missing. Set NGROK_AUTHTOKEN in .env or run: ngrok config add-authtoken <token>")
        return None
    public_url = ngrok.connect(5000, domain=NGROK_DOMAIN)
    return public_url.public_url


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
        public_url = connect_ngrok_tunnel()
        if public_url:
            log("========================================")
            log(f"NGROK URL: {public_url}")
            log("========================================")
        else:
            log("Ngrok skipped (no authtoken). Local bridge is UP at http://127.0.0.1:5000")
            log(f"Expected public URL after auth: https://{NGROK_DOMAIN}")
    except PyngrokError as exc:
        if ping_local():
            log(f"ngrok connect failed ({exc}) but local bridge is UP.")
            if _ngrok_auth_error(exc):
                log("Fix: add NGROK_AUTHTOKEN to .env or run ngrok config add-authtoken <token>")
            else:
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
        self.auth_blocked = not configure_ngrok_auth()
        self.escalated = False

    def run_loop(self):
        while True:
            time.sleep(60)
            self.check_tunnel()

    def check_tunnel(self):
        if self.auth_blocked:
            health_file = self.inbox_dir / "TUNNEL_HEALTH.json"
            health_data = {
                "status": "auth_required",
                "last_check_utc": datetime.now(timezone.utc).isoformat(),
                "consecutive_failures": self.consecutive_failures,
                "last_reconnect_utc": self.last_reconnect_utc.isoformat() if self.last_reconnect_utc else None,
                "uptime_s": (datetime.now(timezone.utc) - self.last_success_utc).total_seconds(),
                "detail": "Ngrok authtoken missing or invalid; watchdog reconnect disabled",
            }
            health_file.write_text(json.dumps(health_data, indent=2), encoding="utf-8")
            return

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
                public_url = connect_ngrok_tunnel()
                if not public_url:
                    raise RuntimeError("Ngrok authtoken missing")
                self.last_reconnect_utc = datetime.now(timezone.utc)
                self.consecutive_failures = 0
            except Exception as exc:
                self.reconnect_failures += 1
                if _ngrok_auth_error(exc):
                    self.auth_blocked = True
                    log("Watchdog: ngrok auth failure detected; stopping reconnect loop.")
                    log("Fix: add NGROK_AUTHTOKEN to .env or run ngrok config add-authtoken <token>")
                    return
                log(f"Watchdog reconnect failed: {exc}")

            if self.reconnect_failures >= 3 and not self.escalated:
                self.escalate_offline()

    def escalate_offline(self):
        self.escalated = True
        log("FATAL: Tunnel cannot self-heal. Recording offline escalation locally.")
        blocker_file = self.inbox_dir / "TUNNEL_BLOCKER.md"
        blocker_file.write_text(
            "NGROK TUNNEL IS DEAD AND CANNOT SELF-HEAL.\n"
            "Local bridge may still be reachable at http://127.0.0.1:5000\n"
            "Check FALLBACK_TUNNEL_URL or configure NGROK_AUTHTOKEN.\n",
            encoding="utf-8",
        )
        response_file = self.inbox_dir / "JULES_RESPONSE.md"
        with response_file.open("a", encoding="utf-8") as f:
            f.write("\n[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.\n")


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
