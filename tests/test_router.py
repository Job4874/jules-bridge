import pytest

from modules.router import dispatch


class TestRouterDispatch:
    def test_routes_code_dev(self):
        result = dispatch({"type": "Code/Dev", "payload": "fix bug"})
        assert result["target"] == "Cursor/Jules"
        assert result["task_type"] == "Code/Dev"

    def test_routes_compute_scale(self):
        result = dispatch({"type": "Compute/Scale", "payload": "scale up"})
        assert result["target"] == "Azure/Local VM"
        assert result["task_type"] == "Compute/Scale"

    def test_routes_routine_ui(self):
        result = dispatch({"type": "Routine/UI", "payload": "click login"})
        assert result["target"] == "human_mimic_driver"
        assert result["task_type"] == "Routine/UI"

    def test_unrouted_when_type_missing(self):
        result = dispatch({"payload": "unknown"})
        assert result["target"] == "UNROUTED"
        assert result["task_type"] == "UNROUTED"

    def test_unrouted_when_type_unknown(self):
        result = dispatch({"type": "Crypto/Trade"})
        assert result["target"] == "UNROUTED"
        assert result["task_type"] == "Crypto/Trade"
