import ctypes
import time
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
MOUSEEVENTF_MOVE = 0x0001

def keep_awake(interval_seconds=540):
    print(f"Keep-awake script started (interval: {interval_seconds}s / {interval_seconds // 60}m).")
    sys.stdout.flush()
    
    is_windows = hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'kernel32')
    if is_windows:
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            print("Windows SetThreadExecutionState activated successfully.")
            sys.stdout.flush()
        except Exception as e:
            print(f"SetThreadExecutionState warning: {e}")
            sys.stdout.flush()

    try:
        count = 0
        while True:
            count += 1
            if is_windows:
                # Nudge mouse 1 pixel right and left as backup pulse
                try:
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
                    time.sleep(0.1)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, 0)
                except Exception as e:
                    pass
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Keep-awake pulse #{count}")
            sys.stdout.flush()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopping keep-awake script...")
        if is_windows:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception:
                pass

if __name__ == "__main__":
    interval = 540
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            pass
    keep_awake(interval)
