"""
guardian.py — Bridge Keep-Alive Guardian
=========================================
Prevents Windows from sleeping, locking, or cutting keyboard/mouse access
while the bridge is running. Starts active protection at 4:00 PM local time.

Features:
  - Mouse jiggle every 55 seconds → prevents Windows screensaver/lock
  - Windows SetThreadExecutionState → prevents display sleep and system sleep
  - PIN unlock: type 4874 + Enter in the console to release control
  - Monitor OFF via PostMessage(SC_MONITORPOWER) — computer stays running
  - Bridge health check every 5 minutes — logs if bridge goes down
  - Auto-start on power recovery via Task Scheduler registration (optional)

Usage:
    python guardian.py                  # starts immediately
    python guardian.py --wait-4pm       # waits until 16:00 local time
    python guardian.py --no-monitor-off # skips turning monitor off
    python guardian.py --pin 9999       # override PIN (default: 4874)

Safe stop: type  4874  then press Enter  in the terminal window.
"""

import argparse
import ctypes
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s guardian: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "guardian.log"),
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("guardian")

# ---------------------------------------------------------------------------
# Windows API constants
# ---------------------------------------------------------------------------

ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

WM_SYSCOMMAND    = 0x0112
SC_MONITORPOWER  = 0xF170
HWND_BROADCAST   = 0xFFFF
MONITOR_OFF      = 2   # PostMessage value for off

# ---------------------------------------------------------------------------
# Windows helpers
# ---------------------------------------------------------------------------

def _prevent_sleep() -> None:
    """Tell Windows: keep the system AND display awake (no screensaver/lock)."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        log.debug("SetThreadExecutionState: awake flags set")
    except Exception as exc:  # noqa: BLE001
        log.warning("SetThreadExecutionState failed: %s", exc)


def _allow_sleep() -> None:
    """Release the sleep-prevention hold."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        log.info("Sleep prevention released.")
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not release sleep state: %s", exc)


def _monitor_off() -> None:
    """Turn off the monitor (computer stays fully running)."""
    try:
        user32 = ctypes.windll.user32
        user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
        log.info("Monitor turned OFF (computer still running).")
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not turn monitor off: %s", exc)


def _jiggle_mouse() -> None:
    """Move mouse 1 pixel and back — imperceptible but resets idle timer."""
    try:
        import pyautogui  # lazy — headless-incompatible
        pyautogui.FAILSAFE = False
        x, y = pyautogui.position()
        pyautogui.moveRel(1, 0, duration=0.05)
        pyautogui.moveRel(-1, 0, duration=0.05)
        log.debug("Mouse jiggled at (%d, %d)", x, y)
    except Exception as exc:  # noqa: BLE001
        log.warning("Mouse jiggle failed: %s", exc)


# ---------------------------------------------------------------------------
# Bridge health check
# ---------------------------------------------------------------------------

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:5000")


def _check_bridge() -> bool:
    """Return True if bridge /health responds ok."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{BRIDGE_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# PIN input listener (runs in background thread)
# ---------------------------------------------------------------------------

def _pin_listener(correct_pin: str, stop_event: threading.Event) -> None:
    """Read lines from stdin. Set stop_event when correct PIN is entered."""
    print(f"\n[Guardian] Running. Type PIN + Enter to unlock and exit.\n", flush=True)
    while not stop_event.is_set():
        try:
            line = input().strip()
            if line == correct_pin:
                log.info("Correct PIN entered — guardian releasing control.")
                stop_event.set()
                return
            elif line:
                print("[Guardian] Wrong PIN. Try again.", flush=True)
        except EOFError:
            # stdin closed (e.g. running without a terminal) — never stop via PIN
            time.sleep(5)
        except Exception as exc:  # noqa: BLE001
            log.warning("PIN listener error: %s", exc)
            time.sleep(1)


# ---------------------------------------------------------------------------
# Task Scheduler registration (optional, for auto-start on power-up)
# ---------------------------------------------------------------------------

def _register_startup_task() -> None:
    """Register this script as a Windows Task Scheduler job on logon."""
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    task_name = "JulesBridgeGuardian"
    cmd = (
        f'schtasks /Create /F /TN "{task_name}" /TR '
        f'\\"{python_exe}\\" \\"{script_path}\\" --wait-4pm'
        f' /SC ONLOGON /RL HIGHEST'
    )
    result = os.system(cmd)
    if result == 0:
        log.info("Startup task registered: %s", task_name)
    else:
        log.warning("Could not register startup task (run as admin for this). Skipping.")


# ---------------------------------------------------------------------------
# Main guardian loop
# ---------------------------------------------------------------------------

def wait_until_4pm() -> None:
    """Block until 16:00:00 local time today (or immediately if past 4pm)."""
    now = datetime.now()
    target = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if now >= target:
        log.info("Already past 4:00 PM — starting immediately.")
        return
    wait_s = (target - now).total_seconds()
    log.info(
        "Waiting until 4:00 PM local time (~%d minutes)... "
        "Current time: %s",
        int(wait_s / 60),
        now.strftime("%H:%M:%S"),
    )
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 30))
    log.info("4:00 PM reached — guardian activating.")


def run_guardian(pin: str, monitor_off: bool, register_startup: bool) -> None:
    stop_event = threading.Event()

    # Start PIN listener thread
    pin_thread = threading.Thread(
        target=_pin_listener, args=(pin, stop_event), daemon=True, name="pin-listener"
    )
    pin_thread.start()

    if register_startup:
        _register_startup_task()

    # Activate Windows sleep prevention
    _prevent_sleep()
    log.info("Sleep/lock prevention ACTIVE. Bridge URL: %s", BRIDGE_URL)
    log.info("PIN to unlock: %s (enter in this terminal)", "*" * len(pin))

    # Turn monitor off after a short delay
    if monitor_off:
        log.info("Monitor will turn off in 5 seconds...")
        time.sleep(5)
        _monitor_off()

    # Main loop
    jiggle_interval = 55      # seconds between mouse jiggles
    health_interval = 300     # seconds between bridge health checks
    last_jiggle = 0.0
    last_health = 0.0

    log.info("Guardian loop running. Press Ctrl+C or enter PIN to stop.")
    while not stop_event.is_set():
        now = time.monotonic()

        if now - last_jiggle >= jiggle_interval:
            _jiggle_mouse()
            _prevent_sleep()   # re-assert every cycle
            last_jiggle = now

        if now - last_health >= health_interval:
            ok = _check_bridge()
            if ok:
                log.info("Bridge health: OK")
            else:
                log.warning(
                    "Bridge health: UNREACHABLE at %s — "
                    "consider restarting bridge.py",
                    BRIDGE_URL,
                )
            last_health = now

        time.sleep(1)

    # Cleanup
    _allow_sleep()
    log.info("Guardian stopped. Keyboard, mouse, and display control released.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jules Bridge Guardian — prevents sleep/lock, unlocks on PIN."
    )
    parser.add_argument(
        "--wait-4pm", action="store_true",
        help="Wait until 4:00 PM local time before activating."
    )
    parser.add_argument(
        "--no-monitor-off", action="store_true",
        help="Skip turning the monitor off."
    )
    parser.add_argument(
        "--pin", default="4874",
        help="Unlock PIN (default: 4874)."
    )
    parser.add_argument(
        "--register-startup", action="store_true",
        help="Register as a Windows Task Scheduler job (run as admin)."
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("JULES BRIDGE GUARDIAN")
    log.info("PIN: %s | Monitor off: %s | Wait for 4pm: %s",
             "*" * len(args.pin), not args.no_monitor_off, args.wait_4pm)
    log.info("=" * 60)

    if args.wait_4pm:
        wait_until_4pm()

    try:
        run_guardian(
            pin=args.pin,
            monitor_off=not args.no_monitor_off,
            register_startup=args.register_startup,
        )
    except KeyboardInterrupt:
        _allow_sleep()
        log.info("Guardian interrupted by Ctrl+C.")


if __name__ == "__main__":
    main()
