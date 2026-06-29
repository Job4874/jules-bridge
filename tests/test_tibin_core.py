import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.tibin_core import compute_rsi

def test_compute_rsi_monotonic_increase():
    """Test RSI with purely increasing values."""
    # 15 values, diff creates 14 diffs, rolling period is 14
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
    rsi = compute_rsi(s, period=14)

    # First 14 values (index 0 to 13) should be NaN due to rolling window of 14 on 15 diffs
    assert rsi.iloc[:14].isna().all(), "Initial values should be NaN due to rolling window"
    # Value at index 14 and 15 should be 100
    assert rsi.iloc[14] == 100.0, "RSI for monotonically increasing series should be 100"
    assert rsi.iloc[15] == 100.0, "RSI for monotonically increasing series should be 100"

def test_compute_rsi_monotonic_decrease():
    """Test RSI with purely decreasing values."""
    s = pd.Series([100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0, -10, -20, -30, -40, -50])
    rsi = compute_rsi(s, period=14)

    assert rsi.iloc[:14].isna().all(), "Initial values should be NaN due to rolling window"
    assert rsi.iloc[14] == 0.0, "RSI for monotonically decreasing series should be 0"
    assert rsi.iloc[15] == 0.0, "RSI for monotonically decreasing series should be 0"

def test_compute_rsi_constant():
    """Test RSI with constant values."""
    s = pd.Series([5] * 16)
    rsi = compute_rsi(s, period=14)

    assert rsi.iloc[:14].isna().all(), "Initial values should be NaN due to rolling window"
    assert rsi.iloc[14] == 50.0, "RSI for constant series should be 50"
    assert rsi.iloc[15] == 50.0, "RSI for constant series should be 50"

def test_compute_rsi_oscillating():
    """Test RSI with oscillating values."""
    s = pd.Series([10, 12, 10, 12, 10, 12, 10, 12, 10, 12])
    rsi = compute_rsi(s, period=4)

    assert rsi.iloc[:4].isna().all(), "Initial values should be NaN due to rolling window"
    assert rsi.iloc[4] == 50.0, "RSI for symmetrically oscillating series should be 50"
    assert rsi.iloc[5] == 50.0, "RSI for symmetrically oscillating series should be 50"

def test_compute_rsi_known_values():
    """Test RSI with a known dataset to ensure formula correctness."""
    np.random.seed(42)
    s = pd.Series(np.random.normal(100, 5, 50))
    rsi = compute_rsi(s, period=14)

    assert len(rsi) == 50
    assert rsi.iloc[:14].isna().all()
    assert not rsi.iloc[14:].isna().any()

    # RSI should be between 0 and 100
    assert (rsi.iloc[14:] >= 0).all()
    assert (rsi.iloc[14:] <= 100).all()
