"""never_power_down.py — Prevent Windows Sleep/Powerdown continuously.

Uses Win32 SetThreadExecutionState (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
and periodic mouse jiggle to override Group Policy and OS idle sleep timeouts.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
import time

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040
MOUSEEVENTF_MOVE = 0x0001


def set_power_prevent_sleep() -> bool:
    try:
        res = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
        )
        return bool(res)
    except Exception:
        return False


def jiggle_mouse() -> None:
    try:
        user32 = ctypes.windll.user32
        user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_MOVE, ctypes.c_ulong(-1).value, 0, 0, 0)
    except Exception:
        pass


def main() -> None:
    print("[ALWAYS-ON] Initializing Win32 power assertion (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)...")
    success = set_power_prevent_sleep()
    print(f"[ALWAYS-ON] SetThreadExecutionState result: {success}")

    pid_path = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Public"), "JulesBridge", "never_power_down.pid")
    os.makedirs(os.path.dirname(pid_path), exist_ok=True)
    with open(pid_path, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    print("[ALWAYS-ON] Running continuous keep-alive loop...")
    sys.stdout.flush()

    while True:
        set_power_prevent_sleep()
        jiggle_mouse()
        time.sleep(30)


if __name__ == "__main__":
    main()
