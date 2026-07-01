"""Shared pytest fixtures."""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolate_jules_rest_env(monkeypatch):
    """Keep local .env REST mode from changing unit-test routing."""
    for key in (
        "JULES_API_KEY",
        "JULES_SOURCE",
        "JULES_USE_REST_API",
        "JULES_API_BASE_URL",
        "JULES_STARTING_BRANCH",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def tmp_dirs():
    """Provide temporary log, memory, and root paths for legacy tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "bridge.log")
        memory_path = os.path.join(tmpdir, "memory")
        os.makedirs(memory_path, exist_ok=True)
        yield {"log": log_path, "memory": memory_path, "root": tmpdir}
