import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from modules import tibin_core

def test_generate_ohlcv():
    df = tibin_core.generate_ohlcv(n=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    expected_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    for col in expected_cols:
        assert col in df.columns

def test_compute_rsi():
    # Provide a series that fluctuates so both gain and loss > 0
    # Length > 14 so rolling window produces valid values
    series = pd.Series([10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10])
    rsi = tibin_core.compute_rsi(series, period=14)
    assert isinstance(rsi, pd.Series)
    assert not rsi.isna().all()
    # Test valid range
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

def test_compute_macd():
    series = pd.Series(np.random.randn(50).cumsum())
    macd_line, signal_line, histogram = tibin_core.compute_macd(series)
    assert isinstance(macd_line, pd.Series)
    assert isinstance(signal_line, pd.Series)
    assert isinstance(histogram, pd.Series)

def test_compute_bollinger():
    series = pd.Series(np.random.randn(50).cumsum())
    upper, sma, lower = tibin_core.compute_bollinger(series, period=20)
    assert isinstance(upper, pd.Series)
    assert isinstance(sma, pd.Series)
    assert isinstance(lower, pd.Series)
    # upper should be >= lower
    valid_idx = ~upper.isna()
    assert (upper[valid_idx] >= lower[valid_idx]).all()

def test_generate_signals():
    df = pd.DataFrame({
        "close": [100, 102, 105, 103, 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 1]
    })
    # Will produce NaNs for the initial periods due to rolling windows, which is fine.
    df_sig = tibin_core.generate_signals(df)
    assert isinstance(df_sig, pd.DataFrame)
    expected_cols = ["rsi", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_mid", "bb_lower", "signal"]
    for col in expected_cols:
        assert col in df_sig.columns
    assert set(df_sig["signal"].unique()).issubset({"HOLD", "BUY", "SELL"})

def test_compute_order_flow():
    df = pd.DataFrame({
        "open": [10, 20, 30],
        "close": [15, 18, 35],
        "volume": [100, 200, 300]
    })
    df_flow = tibin_core.compute_order_flow(df)
    assert isinstance(df_flow, pd.DataFrame)
    expected_cols = ["buy_vol", "sell_vol", "delta", "cvd", "delta_pct"]
    for col in expected_cols:
        assert col in df_flow.columns

def test_run_paper_trading(tmp_path, monkeypatch):
    log_file = tmp_path / "test_trades.log"
    monkeypatch.setattr(tibin_core, "LOG_FILE", log_file)
    monkeypatch.setattr(tibin_core, "INITIAL_CAPITAL", 100000.0)
    monkeypatch.setattr(tibin_core, "SYMBOL", "BTC/USD")

    # Create dummy DataFrame that will trigger BUY and SELL
    # Note: run_paper_trading closes open positions at the end automatically!
    # If we BUY and SELL properly, the force-close shouldn't trigger an extra trade.
    df = pd.DataFrame({
        "signal": ["HOLD", "BUY", "HOLD", "SELL", "HOLD"],
        "close": [100, 100, 110, 120, 120],
        "delta_pct": [0.0, 0.1, 0.0, -0.1, 0.0],
        "timestamp": [
            datetime(2025, 1, 1, 10, 0),
            datetime(2025, 1, 1, 11, 0),
            datetime(2025, 1, 1, 12, 0),
            datetime(2025, 1, 1, 13, 0),
            datetime(2025, 1, 1, 14, 0)
        ]
    })

    result = tibin_core.run_paper_trading(df)
    assert isinstance(result, dict)
    expected_keys = ["total_trades", "wins", "losses", "win_rate", "total_pnl_usd", "final_capital", "log_lines"]
    for key in expected_keys:
        assert key in result

    # The dictionary records one trade cycle as either a win or loss.
    # We started with 0 trades.
    # At index 1: BUY. Position becomes positive.
    # At index 3: SELL. Proceeds are calculated, win/loss incremented. That counts as 1 trade.
    # At index 4: HOLD. No action.
    # End of df: position is 0, so no force close.
    # total_trades = wins + losses = 1.
    assert result["total_trades"] == 1
    assert result["wins"] == 1
    assert log_file.exists()
