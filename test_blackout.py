"""
test_blackout.py — Quick test of guardian blackout protocol.

Tests in sequence:
  1. SetThreadExecutionState (sleep prevention)
  2. Mouse jiggle (pyautogui)
  3. Monitor OFF signal (PostMessage SC_MONITORPOWER)

Run:
    python test_blackout.py             # dry-run, skips monitor off
    python test_blackout.py --live      # LIVE: actually turns monitor off
    python test_blackout.py --live --delay 3   # turns off after 3 seconds
"""

import argparse
import ctypes
import sys
import time

# ── Windows API ─────────────────────────────────────────────────────────────

ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

WM_SYSCOMMAND   = 0x0112
SC_MONITORPOWER = 0xF170
HWND_BROADCAST  = 0xFFFF
MONITOR_OFF     = 2


def _test_sleep_prevention() -> tuple[bool, str]:
    try:
        ret = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        if ret == 0:
            return False, "SetThreadExecutionState returned 0 (failed)"
        return True, f"SetThreadExecutionState OK (prev state: 0x{ret:08X})"
    except Exception as exc:
        return False, f"SetThreadExecutionState ERROR: {exc}"


def _test_mouse_jiggle() -> tuple[bool, str]:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        x, y = pyautogui.position()
        pyautogui.moveRel(1, 0, duration=0.05)
        pyautogui.moveRel(-1, 0, duration=0.05)
        x2, y2 = pyautogui.position()
        return True, f"Mouse jiggle OK — position before=({x},{y}) after=({x2},{y2})"
    except ImportError:
        return False, "pyautogui not installed — run: pip install pyautogui"
    except Exception as exc:
        return False, f"Mouse jiggle ERROR: {exc}"


def _test_monitor_off(dry_run: bool = True, delay_s: int = 2) -> tuple[bool, str]:
    if dry_run:
        return True, "Monitor OFF skipped (dry-run). Pass --live to actually turn off."
    try:
        print(f"  [!] Monitor turning OFF in {delay_s} second(s)... (move mouse to wake)")
        time.sleep(delay_s)
        user32 = ctypes.windll.user32
        ret = user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
        if ret == 0:
            return False, "PostMessageW returned 0 (might have failed)"
        return True, "PostMessageW SC_MONITORPOWER sent — monitor should be OFF"
    except Exception as exc:
        return False, f"Monitor OFF ERROR: {exc}"


def _release_sleep_prevention() -> None:
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        pass


# ── Runner ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test guardian blackout protocol.")
    parser.add_argument("--live", action="store_true",
                        help="Actually turn monitor off (default: dry-run)")
    parser.add_argument("--delay", type=int, default=2,
                        help="Seconds before monitor turns off (default: 2)")
    args = parser.parse_args()

    mode = "LIVE" if args.live else "DRY-RUN"
    print("=" * 55)
    print(f"  GUARDIAN BLACKOUT PROTOCOL TEST  [{mode}]")
    print("=" * 55)

    tests = [
        ("Sleep prevention (SetThreadExecutionState)", _test_sleep_prevention),
        ("Mouse jiggle (pyautogui)",                  _test_mouse_jiggle),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        print(f"\n[TEST] {name}")
        ok, msg = fn()
        status = "  ✅ PASS" if ok else "  ❌ FAIL"
        print(f"{status}: {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    # Monitor off test last
    print(f"\n[TEST] Monitor OFF signal (PostMessage SC_MONITORPOWER)")
    ok, msg = _test_monitor_off(dry_run=not args.live, delay_s=args.delay)
    status = "  ✅ PASS" if ok else "  ❌ FAIL"
    print(f"{status}: {msg}")
    if ok:
        passed += 1
    else:
        failed += 1

    # Release
    _release_sleep_prevention()

    print("\n" + "=" * 55)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 55)

    if args.live:
        print("\n  Move mouse or press any key to wake the monitor.")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
