import pytest
from modules.router import dispatch

def test_dispatch_code_dev():
    assert dispatch({"type": "Code/Dev"}) == "Cursor/Jules"

def test_dispatch_compute_scale():
    assert dispatch({"type": "Compute/Scale"}) == "Azure/Local VM"

def test_dispatch_routine_ui():
    assert dispatch({"type": "Routine/UI"}) == "human_mimic_driver"

def test_dispatch_unknown():
    assert dispatch({"type": "Unknown"}) == "UNROUTED"
