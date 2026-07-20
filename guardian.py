"""
guardian.py — Bridge Keep-Alive Guardian
=========================================
Keeps the computer awake but the monitor BLACK until PIN 4874 is entered.

How it works:
  - Sends SC_MONITORPOWER every 8 seconds — mouse waking it doesn't matter
  - Captures keystrokes with msvcrt.getch() (no terminal focus needed)
  - Type 4874 then Enter → monitor released, guardian exits
  - SetThreadExecutionState keeps CPU alive so computer never sleeps
  - Mouse jiggle via ctypes every 55 seconds resets Windows idle timer

Usage:
    python guardian.py               # starts immediately
    python guardian.py --wait-4pm    # waits until 16:00 local time
    python guardian.py --pin 9999    # override PIN (default: 4874)

Stop: type 4874 then press Enter (works with monitor off)
"""

import argparse
import ctypes
import ctypes.wintypes
import logging
import msvcrt
import os
import sys
import threading
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s guardian: %(message)s",
    datefmt="%H:%M:%S",
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
# Win32 constants
# ---------------------------------------------------------------------------

ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
WM_SYSCOMMAND       = 0x0112
SC_MONITORPOWER     = 0xF170
HWND_BROADCAST      = 0xFFFF
MONITOR_OFF         = 2
MOUSEEVENTF_MOVE    = 0x0001

# ---------------------------------------------------------------------------
# Win32 helpers
# ---------------------------------------------------------------------------

def _prevent_sleep() -> None:
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
    except Exception as exc:
        log.warning("SetThreadExecutionState failed: %s", exc)


def _allow_sleep() -> None:
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception as exc:
        log.warning("_allow_sleep failed: %s", exc)


def _send_monitor_off() -> None:
    """Send monitor-off signal. Call repeatedly — mouse movement will wake it."""
    try:
        ctypes.windll.user32.PostMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF
        )
    except Exception as exc:
        log.warning("Monitor off signal failed: %s", exc)


def _jiggle_mouse() -> None:
    """Tiny mouse nudge via ctypes — resets Windows idle timer."""
    try:
        user32 = ctypes.windll.user32
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_MOVE, ctypes.c_ulong(-1).value, 0, 0, 0)
    except Exception as exc:
        log.warning("Mouse jiggle failed: %s", exc)

# ---------------------------------------------------------------------------
# Bridge health check
# ---------------------------------------------------------------------------

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:5000")


def _check_bridge() -> bool:
    try:
        import urllib.request, json
        with urllib.request.urlopen(f"{BRIDGE_URL}/health", timeout=8) as r:
            return json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Continuous monitor-off thread
# Re-sends every MONITOR_OFF_INTERVAL seconds so mouse movement can't wake it
# ---------------------------------------------------------------------------

MONITOR_OFF_INTERVAL = 8   # seconds — shorter = harder to wake with mouse


def _monitor_off_loop(stop_event: threading.Event) -> None:
    """Keep sending monitor-off every N seconds until stop_event is set."""
    log.info("Monitor-off loop started (every %ds)", MONITOR_OFF_INTERVAL)
    while not stop_event.is_set():
        _send_monitor_off()
        stop_event.wait(timeout=MONITOR_OFF_INTERVAL)
    log.info("Monitor-off loop stopped — display released.")

# ---------------------------------------------------------------------------
# PIN listener via msvcrt (works even with monitor off, no terminal focus req)
# ---------------------------------------------------------------------------

def _pin_listener(correct_pin: str, stop_event: threading.Event) -> None:
    """
    Read individual keystrokes with msvcrt.getch().
    Accumulates chars; clears buffer on Enter if wrong PIN.
    Sets stop_event when correct PIN + Enter is detected.
    """
    buf: list[str] = []
    log.info("PIN listener ready. Type %s + Enter to unlock.", "*" * len(correct_pin))
    while not stop_event.is_set():
        try:
            if msvcrt.kbhit():
                raw = msvcrt.getch()
                # Enter key
                if raw in (b"\r", b"\n"):
                    entered = "".join(buf)
                    if entered == correct_pin:
                        log.info("Correct PIN — releasing guardian.")
                        stop_event.set()
                        return
                    else:
                        log.warning("Wrong PIN entered (%d chars). Try again.", len(entered))
                        buf.clear()
                # Backspace
                elif raw == b"\x08":
                    if buf:
                        buf.pop()
                # Printable char
                else:
                    try:
                        buf.append(raw.decode("utf-8"))
                    except UnicodeDecodeError:
                        buf.clear()
            else:
                time.sleep(0.05)
        except Exception as exc:
            log.warning("PIN listener error: %s", exc)
            time.sleep(0.5)

# ---------------------------------------------------------------------------
# Wait until 4pm
# ---------------------------------------------------------------------------

def wait_until_4pm() -> None:
    now = datetime.now()
    target = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if now >= target:
        log.info("Already past 4:00 PM — activating immediately.")
        return
    wait_s = (target - now).total_seconds()
    log.info("Waiting until 4:00 PM (~%d min). Time now: %s",
             int(wait_s / 60), now.strftime("%H:%M:%S"))
    while True:
        rem = (target - datetime.now()).total_seconds()
        if rem <= 0:
            break
        time.sleep(min(rem, 10))
    log.info("4:00 PM — guardian activating NOW.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_guardian(pin: str) -> None:
    stop_event = threading.Event()

    _prevent_sleep()

    # Thread 1: continuously re-kill the monitor
    mon_thread = threading.Thread(
        target=_monitor_off_loop, args=(stop_event,), daemon=True, name="monitor-off"
    )
    mon_thread.start()

    # Thread 2: PIN listener
    pin_thread = threading.Thread(
        target=_pin_listener, args=(pin, stop_event), daemon=True, name="pin-listener"
    )
    pin_thread.start()

    log.info("=" * 50)
    log.info("GUARDIAN ACTIVE")
    log.info("Monitor will go off in %ds and re-off every %ds",
             MONITOR_OFF_INTERVAL, MONITOR_OFF_INTERVAL)
    log.info("Type PIN + Enter to unlock: %s", "*" * len(pin))
    log.info("=" * 50)

    # Main loop: keep-alive + bridge health
    jiggle_interval  = 55
    health_interval  = 300
    last_jiggle      = 0.0
    last_health      = 0.0

    while not stop_event.is_set():
        now = time.monotonic()
        if now - last_jiggle >= jiggle_interval:
            _jiggle_mouse()
            _prevent_sleep()
            last_jiggle = now
        if now - last_health >= health_interval:
            if _check_bridge():
                log.info("Bridge health: OK")
            else:
                log.warning("Bridge health: UNREACHABLE — is bridge.py running?")
            last_health = now
        time.sleep(0.5)

    _allow_sleep()
    log.info("Guardian stopped. Monitor and sleep control released.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jules Bridge Guardian")
    parser.add_argument("--wait-4pm", action="store_true",
                        help="Wait until 4:00 PM before activating.")
    parser.add_argument("--pin", default="4874", help="Unlock PIN (default: 4874)")
    args = parser.parse_args()

    if args.wait_4pm:
        wait_until_4pm()

    try:
        run_guardian(pin=args.pin)
    except KeyboardInterrupt:
        _allow_sleep()
        log.info("Guardian interrupted (Ctrl+C).")


if __name__ == "__main__":
    main()
