
import sys
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest
import time
import json

# We must ensure msvcrt and ctypes.windll exist for importing guardian
sys_modules_patched = False
if "msvcrt" not in sys.modules:
    sys.modules["msvcrt"] = MagicMock()
    sys_modules_patched = True

import ctypes
if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
if not hasattr(ctypes, "wintypes"):
    ctypes.wintypes = MagicMock()

import guardian



@patch("guardian.ctypes.windll.kernel32.SetThreadExecutionState")
def test_prevent_sleep(mock_set_thread_execution_state):
    guardian._prevent_sleep()
    mock_set_thread_execution_state.assert_called_once_with(
        guardian.ES_CONTINUOUS | guardian.ES_SYSTEM_REQUIRED | guardian.ES_DISPLAY_REQUIRED
    )


@patch("guardian.ctypes.windll.kernel32.SetThreadExecutionState")
def test_prevent_sleep_exception(mock_set_thread_execution_state, caplog):
    mock_set_thread_execution_state.side_effect = Exception("Test Error")
    guardian._prevent_sleep()
    assert "SetThreadExecutionState failed" in caplog.text


@patch("guardian.ctypes.windll.kernel32.SetThreadExecutionState")
def test_allow_sleep(mock_set_thread_execution_state):
    guardian._allow_sleep()
    mock_set_thread_execution_state.assert_called_once_with(guardian.ES_CONTINUOUS)


@patch("guardian.ctypes.windll.kernel32.SetThreadExecutionState")
def test_allow_sleep_exception(mock_set_thread_execution_state, caplog):
    mock_set_thread_execution_state.side_effect = Exception("Test Error")
    guardian._allow_sleep()
    assert "_allow_sleep failed" in caplog.text


@patch("guardian.ctypes.windll.user32.PostMessageW")
def test_send_monitor_off(mock_post_message_w):
    guardian._send_monitor_off()
    mock_post_message_w.assert_called_once_with(
        guardian.HWND_BROADCAST, guardian.WM_SYSCOMMAND, guardian.SC_MONITORPOWER, guardian.MONITOR_OFF
    )


@patch("guardian.ctypes.windll.user32.PostMessageW")
def test_send_monitor_off_exception(mock_post_message_w, caplog):
    mock_post_message_w.side_effect = Exception("Test Error")
    guardian._send_monitor_off()
    assert "Monitor off signal failed" in caplog.text


@patch("guardian.ctypes.wintypes.POINT")
@patch("guardian.ctypes.byref")
@patch("guardian.ctypes.windll.user32.GetCursorPos")
@patch("guardian.ctypes.windll.user32.mouse_event")
@patch("guardian.time.sleep")
def test_jiggle_mouse(mock_sleep, mock_mouse_event, mock_get_cursor_pos, mock_byref, mock_point):
    mock_point_instance = MagicMock()
    mock_point.return_value = mock_point_instance

    guardian._jiggle_mouse()

    mock_get_cursor_pos.assert_called_once()
    assert mock_mouse_event.call_count == 2
    mock_sleep.assert_called_once_with(0.05)


@patch("guardian.ctypes.windll.user32.GetCursorPos")
def test_jiggle_mouse_exception(mock_get_cursor_pos, caplog):
    mock_get_cursor_pos.side_effect = Exception("Test Error")
    guardian._jiggle_mouse()
    assert "Mouse jiggle failed" in caplog.text


@patch("urllib.request.urlopen")
def test_check_bridge_ok(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
    # Mock context manager
    mock_urlopen.return_value.__enter__.return_value = mock_response

    assert guardian._check_bridge() is True


@patch("urllib.request.urlopen")
def test_check_bridge_fail(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"status": "error"}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    assert guardian._check_bridge() is False


@patch("urllib.request.urlopen")
def test_check_bridge_exception(mock_urlopen):
    mock_urlopen.side_effect = Exception("Test Error")
    assert guardian._check_bridge() is False


@patch("guardian._send_monitor_off")
def test_monitor_off_loop(mock_send_monitor_off):
    stop_event = threading.Event()

    def set_stop():
        time.sleep(0.01) # Small delay to allow one iteration
        stop_event.set()

    threading.Thread(target=set_stop).start()
    guardian._monitor_off_loop(stop_event)

    assert mock_send_monitor_off.call_count > 0


@patch("guardian.msvcrt.kbhit")
@patch("guardian.msvcrt.getch")
def test_pin_listener_correct(mock_getch, mock_kbhit):
    stop_event = threading.Event()
    # Simulate keys: '4', '8', '7', '4', Enter
    mock_kbhit.return_value = True
    mock_getch.side_effect = [b'4', b'8', b'7', b'4', b'\r']

    guardian._pin_listener("4874", stop_event)
    assert stop_event.is_set()


@patch("guardian.msvcrt.kbhit")
@patch("guardian.msvcrt.getch")
@patch("guardian.time.sleep") # Prevent infinite loop spinning fast if error
def test_pin_listener_incorrect_then_correct(mock_sleep, mock_getch, mock_kbhit, caplog):
    stop_event = threading.Event()
    mock_kbhit.return_value = True
    # Simulate: '1', '2', Enter (wrong), '4', '8', '7', '4', Enter (correct)
    mock_getch.side_effect = [b'1', b'2', b'\r', b'4', b'8', b'7', b'4', b'\r']

    guardian._pin_listener("4874", stop_event)
    assert stop_event.is_set()
    assert "Wrong PIN entered (2 chars). Try again." in caplog.text


@patch("guardian.msvcrt.kbhit")
@patch("guardian.msvcrt.getch")
def test_pin_listener_backspace(mock_getch, mock_kbhit):
    stop_event = threading.Event()
    mock_kbhit.return_value = True
    # Simulate: '4', '8', '9', Backspace, '7', '4', Enter
    mock_getch.side_effect = [b'4', b'8', b'9', b'\x08', b'7', b'4', b'\r']

    guardian._pin_listener("4874", stop_event)
    assert stop_event.is_set()


@patch("guardian.msvcrt.kbhit")
@patch("guardian.time.sleep")
def test_pin_listener_no_kbhit(mock_sleep, mock_kbhit):
    stop_event = threading.Event()
    mock_kbhit.return_value = False

    def set_stop():
        time.sleep(0.01)
        stop_event.set()

    threading.Thread(target=set_stop).start()
    guardian._pin_listener("4874", stop_event)

    assert stop_event.is_set()
    mock_sleep.assert_called()


@patch("guardian.msvcrt.kbhit")
@patch("guardian.msvcrt.getch")
@patch("guardian.time.sleep")
def test_pin_listener_exception(mock_sleep, mock_getch, mock_kbhit, caplog):
    stop_event = threading.Event()
    mock_kbhit.return_value = True
    mock_getch.side_effect = [Exception("Test Error"), b'4', b'8', b'7', b'4', b'\r']

    guardian._pin_listener("4874", stop_event)

    assert stop_event.is_set()
    assert "PIN listener error: Test Error" in caplog.text


@patch("guardian.datetime")
@patch("guardian.time.sleep")
def test_wait_until_4pm_already_past(mock_sleep, mock_datetime):
    # Mock now to be 5 PM
    now = datetime(2023, 1, 1, 17, 0, 0)
    mock_datetime.now.return_value = now

    guardian.wait_until_4pm()
    mock_sleep.assert_not_called()


@patch("guardian.datetime")
@patch("guardian.time.sleep")
def test_wait_until_4pm_wait(mock_sleep, mock_datetime):
    # Initial now: 3:59:50 PM
    initial_time = datetime(2023, 1, 1, 15, 59, 50)
    # Target is 4:00:00 PM

    # We need datetime.now() to return different values on subsequent calls
    # First call: set target
    # Second call: calculate rem in loop
    # Third call: calculate rem in loop (should be <= 0)
    mock_datetime.now.side_effect = [
        initial_time,
        initial_time,
        datetime(2023, 1, 1, 16, 0, 0)
    ]

    guardian.wait_until_4pm()
    mock_sleep.assert_called()


@patch("guardian._prevent_sleep")
@patch("guardian._jiggle_mouse")
@patch("guardian._check_bridge")
@patch("guardian._allow_sleep")
@patch("guardian.time.sleep")
@patch("guardian.time.monotonic")
def test_run_guardian(mock_monotonic, mock_sleep, mock_allow_sleep, mock_check_bridge, mock_jiggle_mouse, mock_prevent_sleep):
    # We want to test that the loop runs, checks bridge, jiggles, and stops
    mock_monotonic.side_effect = [
        0.0, # initial jiggle/health check
        60.0, # triggers jiggle, triggers health check if health interval was smaller, but it's 300
        300.0, # triggers both
        301.0,
        302.0
    ]

    stop_event_ref = []
    original_thread = threading.Thread
    def mock_thread(*args, **kwargs):
        if kwargs.get('name') == 'pin-listener':
            stop_event = kwargs['args'][1]
            stop_event_ref.append(stop_event)
            # Do nothing in the thread so it doesn't exit prematurely
            kwargs['target'] = lambda *a, **k: None
            kwargs['args'] = ()
        return original_thread(*args, **kwargs)

    def custom_sleep(secs):
        if len(stop_event_ref) > 0:
            if mock_monotonic.call_count >= 3:
                stop_event_ref[0].set()

    mock_sleep.side_effect = custom_sleep

    with patch("guardian.threading.Thread", side_effect=mock_thread):
        guardian.run_guardian("4874")

    mock_prevent_sleep.assert_called()
    mock_allow_sleep.assert_called_once()
    mock_check_bridge.assert_called()


@patch("guardian.run_guardian")
@patch("guardian.wait_until_4pm")
@patch("guardian.argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_wait_until_4pm, mock_run_guardian):
    args = MagicMock()
    args.wait_4pm = True
    args.pin = "1234"
    mock_parse_args.return_value = args

    guardian.main()

    mock_wait_until_4pm.assert_called_once()
    mock_run_guardian.assert_called_once_with(pin="1234")


@patch("guardian.run_guardian")
@patch("guardian.argparse.ArgumentParser.parse_args")
@patch("guardian._allow_sleep")
def test_main_keyboard_interrupt(mock_allow_sleep, mock_parse_args, mock_run_guardian):
    args = MagicMock()
    args.wait_4pm = False
    args.pin = "1234"
    mock_parse_args.return_value = args

    mock_run_guardian.side_effect = KeyboardInterrupt()

    guardian.main()

    mock_allow_sleep.assert_called_once()
