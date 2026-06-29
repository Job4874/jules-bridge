"""Tests for tibin_core.py signal generation and utility modules."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure modules are discoverable
sys.path.append(str(Path.cwd()))
from modules.tibin_core import generate_ohlcv

def test_generate_ohlcv_shape_and_columns():
    """Test that generate_ohlcv returns correct dimensions and column names."""
    n_candles = 100
    df = generate_ohlcv(n=n_candles)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == n_candles

    expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]
    assert list(df.columns) == expected_columns

def test_generate_ohlcv_determinism():
    """Test that using the same seed produces identical results."""
    n_candles = 50
    seed = 123

    df1 = generate_ohlcv(n=n_candles, seed=seed)
    df2 = generate_ohlcv(n=n_candles, seed=seed)

    pd.testing.assert_frame_equal(df1, df2)

    # Check different seed produces different results
    df3 = generate_ohlcv(n=n_candles, seed=456)
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(df1, df3)

def test_generate_ohlcv_price_logic():
    """Test that OHLC rules hold (high >= open, close; low <= open, close)."""
    n_candles = 200
    df = generate_ohlcv(n=n_candles)

    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()

    # Check volume is positive
    assert (df["volume"] >= 0).all()

def test_generate_ohlcv_datatypes():
    """Test that the data types for each column are correct."""
    df = generate_ohlcv(n=10)

    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    for col in ["open", "high", "low", "close", "volume"]:
        assert pd.api.types.is_numeric_dtype(df[col])

def test_generate_ohlcv_edge_cases():
    """Test boundary conditions like requesting 1 candle."""
    df = generate_ohlcv(n=1)
    assert len(df) == 1
    # Only close is exactly 67500.0, open has noise applied
    assert df["close"].iloc[0] == 67500.0
    assert "timestamp" in df.columns
