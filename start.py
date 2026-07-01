"""Launch Jules Bridge locally and expose it through the reserved ngrok domain."""
import json
import logging
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pyngrok import ngrok
from pyngrok.exception import PyngrokError

from modules.jules_env import configure_ngrok_auth, ensure_persistent_secrets, load_env

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bridge.log"
NGROK_DOMAIN = "parade-marrow-pulp.ngrok-free.dev"
NGROK_PUBLIC_URL = f"https://{NGROK_DOMAIN}"
NGROK_REQUEST_HEADERS = {"ngrok-skip-browser-warning": "true"}


class _BridgeState:
    """Mutable launcher state shared by startup and shutdown hooks."""

    flask_process: subprocess.Popen | None = None
    last_ngrok_error: str = ""


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


def ping_public() -> tuple[bool, str]:
    """Return public tunnel health and any error detail."""
    request = urllib.request.Request(
        f"{NGROK_PUBLIC_URL}/ping",
        headers=NGROK_REQUEST_HEADERS,
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            if resp.status == 200:
                return True, ""
            return False, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except OSError as exc:
        return False, str(exc)


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


def clear_tunnel_blocker(inbox_dir: Path) -> None:
    blocker_file = inbox_dir / "TUNNEL_BLOCKER.md"
    if blocker_file.is_file():
        blocker_file.unlink()


def connect_ngrok() -> str:
    """Configure auth and bind the reserved ngrok domain."""
    ngrok_ok, ngrok_detail = configure_ngrok_auth()
    if not ngrok_ok:
        STATE.last_ngrok_error = ngrok_detail
        raise PyngrokError(ngrok_detail)

    public_url = ngrok.connect(5000, domain=NGROK_DOMAIN)
    public_ping_ok, public_ping_detail = ping_public()
    if not public_ping_ok:
        STATE.last_ngrok_error = public_ping_detail or "public /ping check failed"
        raise PyngrokError(STATE.last_ngrok_error)

    clear_tunnel_blocker(ROOT / "jules_inbox")
    STATE.last_ngrok_error = ""
    return public_url.public_url


def main():
    load_env()
    secret_status = ensure_persistent_secrets()
    log(f"Persistent secrets ready (mirror={secret_status['mirror_path']})")
    if not secret_status["ngrok_configured"]:
        log(f"ERROR: {secret_status['ngrok_detail']}")
        log("Run: .\\scripts\\Ensure-JulesSecrets.ps1 -NgrokAuthtoken <token>")
        log("Get token: https://dashboard.ngrok.com/get-started/your-authtoken")
        sys.exit(1)

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
        public_url = connect_ngrok()
        log("========================================")
        log(f"NGROK URL: {public_url}")
        log("========================================")
    except PyngrokError as exc:
        STATE.last_ngrok_error = str(exc)
        log(f"FATAL: ngrok connect failed ({exc})")
        log("Fix auth with: .\\scripts\\Ensure-JulesSecrets.ps1 -NgrokAuthtoken <token>")
        stop_flask()
        sys.exit(1)


class TunnelWatchdog:
    def __init__(self, inbox_dir=ROOT / "jules_inbox"):
        self.inbox_dir = inbox_dir
        self.consecutive_failures = 0
        self.reconnect_failures = 0
        self.last_reconnect_utc = None
        self.last_success_utc = datetime.now(timezone.utc)
        self.last_error = ""

    def run_loop(self):
        while True:
            time.sleep(60)
            self.check_tunnel()

    def check_tunnel(self):
        public_ok, public_detail = ping_public()
        if public_ok:
            self.consecutive_failures = 0
            self.reconnect_failures = 0
            self.last_success_utc = datetime.now(timezone.utc)
            self.last_error = ""
        else:
            self.consecutive_failures += 1
            self.last_error = public_detail or STATE.last_ngrok_error or "public ping failed"

        uptime_s = (datetime.now(timezone.utc) - self.last_success_utc).total_seconds()
        status = "healthy" if self.consecutive_failures == 0 else "reconnecting" if self.consecutive_failures >= 3 else "degraded"

        health_file = self.inbox_dir / "TUNNEL_HEALTH.json"
        health_data = {
            "status": status,
            "last_check_utc": datetime.now(timezone.utc).isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "last_reconnect_utc": self.last_reconnect_utc.isoformat() if self.last_reconnect_utc else None,
            "last_error": self.last_error,
            "uptime_s": uptime_s,
        }
        health_file.write_text(json.dumps(health_data, indent=2), encoding="utf-8")

        if self.consecutive_failures >= 3:
            log(f"Watchdog: {self.consecutive_failures} failures. Reconnecting ngrok...")
            try:
                ngrok.kill()
                time.sleep(1)
                connect_ngrok()
                self.last_reconnect_utc = datetime.now(timezone.utc)
                self.consecutive_failures = 0
                self.reconnect_failures = 0
                self.last_error = ""
            except Exception as exc:
                self.reconnect_failures += 1
                self.last_error = str(exc)
                log(f"Watchdog reconnect failed: {exc}")

            if self.reconnect_failures == 3:
                self.escalate_offline()

    def escalate_offline(self):
        log("FATAL: Tunnel cannot self-heal. Triggering Git offline escalation.")
        blocker_file = self.inbox_dir / "TUNNEL_BLOCKER.md"
        blocker_file.write_text(
            "\n".join(
                [
                    "NGROK TUNNEL IS DEAD AND CANNOT SELF-HEAL.",
                    "",
                    f"Last error: {self.last_error or STATE.last_ngrok_error or 'unknown'}",
                    "",
                    "Fix:",
                    "  .\\scripts\\Ensure-JulesSecrets.ps1 -NgrokAuthtoken <token>",
                    "  .\\Run-JulesBridge.cmd",
                ]
            ),
            encoding="utf-8",
        )
        response_file = self.inbox_dir / "JULES_RESPONSE.md"
        with response_file.open("a", encoding="utf-8") as handle:
            handle.write("\n[TUNNEL_DEAD] Ngrok tunnel cannot self-heal.\n")

        try:
            subprocess.run(["git", "add", str(blocker_file), str(response_file), str(self.inbox_dir / "TUNNEL_HEALTH.json")], cwd=str(ROOT), check=True)
            subprocess.run(["git", "commit", "-m", "[TUNNEL_DEAD] Ngrok tunnel cannot self-heal"], cwd=str(ROOT), check=True)
            subprocess.run(["git", "push"], cwd=str(ROOT), check=True)
        except subprocess.CalledProcessError as exc:
            log(f"Failed to push offline escalation: {exc}")


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
