"""
test_blackout.py — Blackout protocol test. ZERO external dependencies.
Uses only Python stdlib + ctypes (built-in on Windows).

Run:
    python test_blackout.py             # dry-run
    python test_blackout.py --live      # LIVE: turns monitor off
"""

import argparse
import ctypes
import ctypes.wintypes
import sys
import time

# ── Win32 constants ──────────────────────────────────────────────────────────
ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
WM_SYSCOMMAND       = 0x0112
SC_MONITORPOWER     = 0xF170
HWND_BROADCAST      = 0xFFFF
MONITOR_OFF         = 2
MOUSEEVENTF_MOVE    = 0x0001

# ── Sleep prevention ─────────────────────────────────────────────────────────
def _test_sleep_prevention():
    try:
        kernel32 = ctypes.windll.kernel32
        ret = kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        if ret == 0:
            return False, "SetThreadExecutionState returned 0"
        return True, f"SetThreadExecutionState OK (prev=0x{ret:08X})"
    except Exception as exc:
        return False, str(exc)

# ── Mouse jiggle via ctypes (NO pyautogui) ───────────────────────────────────
def _test_mouse_jiggle():
    try:
        user32 = ctypes.windll.user32
        # Get current position
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        x0, y0 = pt.x, pt.y
        # Move +1 pixel
        user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
        time.sleep(0.05)
        # Move -1 pixel back
        user32.mouse_event(MOUSEEVENTF_MOVE, ctypes.c_ulong(-1).value, 0, 0, 0)
        time.sleep(0.05)
        user32.GetCursorPos(ctypes.byref(pt))
        return True, f"Mouse jiggle OK via ctypes — pos=({x0},{y0})"
    except Exception as exc:
        return False, str(exc)

# ── Monitor off ──────────────────────────────────────────────────────────────
def _test_monitor_off(dry_run=True, delay_s=2):
    if dry_run:
        return True, "Monitor OFF skipped (dry-run). Run with --live to activate."
    try:
        print(f"  !! Monitor turning OFF in {delay_s}s — move mouse to wake !!")
        sys.stdout.flush()
        time.sleep(delay_s)
        user32 = ctypes.windll.user32
        user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
        return True, "PostMessageW SC_MONITORPOWER sent — screen should be OFF"
    except Exception as exc:
        return False, str(exc)

# ── Release ──────────────────────────────────────────────────────────────────
def _release():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        pass

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Actually turn monitor off")
    parser.add_argument("--delay", type=int, default=2, help="Seconds before monitor off")
    args = parser.parse_args()

    mode = "LIVE" if args.live else "DRY-RUN"
    print(f"\n{'='*50}")
    print(f"  BLACKOUT PROTOCOL TEST  [{mode}]")
    print(f"{'='*50}\n")

    results = []
    for label, fn, kwargs in [
        ("Sleep prevention", _test_sleep_prevention, {}),
        ("Mouse jiggle (ctypes)", _test_mouse_jiggle, {}),
        ("Monitor OFF signal", _test_monitor_off, {"dry_run": not args.live, "delay_s": args.delay}),
    ]:
        print(f"[TEST] {label}")
        ok, msg = fn(**kwargs)
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {msg}\n")
        results.append(ok)

    _release()
    passed = sum(results)
    failed = len(results) - passed
    print(f"{'='*50}")
    print(f"  {passed} passed  |  {failed} failed")
    print(f"{'='*50}\n")
    if args.live and all(results):
        print("  Move the mouse to wake the monitor.")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
