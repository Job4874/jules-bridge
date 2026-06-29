import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from modules.tibin_core import generate_signals

def test_generate_signals_expected_columns():
    """Verify that generate_signals adds all expected indicator and signal columns."""
    df = pd.DataFrame({
        "close": [10, 11, 12, 11, 10] * 5  # Ensure enough data points for indicators
    })

    result = generate_signals(df)

    expected_columns = [
        "rsi", "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_mid", "bb_lower", "signal"
    ]
    for col in expected_columns:
        assert col in result.columns

@patch("modules.tibin_core.compute_rsi")
@patch("modules.tibin_core.compute_macd")
@patch("modules.tibin_core.compute_bollinger")
def test_generate_signals_buy_trigger(mock_bollinger, mock_macd, mock_rsi):
    """Verify BUY signal when 2+ buy confirmations occur."""
    df = pd.DataFrame({"close": [100.0, 100.0, 100.0]})

    # Setup mock returns
    # 1. RSI buy: rsi < 35 (True)
    mock_rsi.return_value = pd.Series([30.0, 30.0, 30.0])

    # 2. MACD buy: macd > macd_signal & macd_hist > 0 (True)
    mock_macd.return_value = (
        pd.Series([2.0, 2.0, 2.0]),  # macd
        pd.Series([1.0, 1.0, 1.0]),  # macd_signal
        pd.Series([1.0, 1.0, 1.0])   # macd_hist
    )

    # 3. BB buy: close < bb_lower (False, meaning buy score = 2)
    mock_bollinger.return_value = (
        pd.Series([110.0, 110.0, 110.0]), # bb_upper
        pd.Series([100.0, 100.0, 100.0]), # bb_mid
        pd.Series([90.0, 90.0, 90.0])     # bb_lower
    )

    result = generate_signals(df)

    # buy_score = 1 (RSI) + 1 (MACD) + 0 (BB) = 2 -> BUY
    assert all(result["signal"] == "BUY")

@patch("modules.tibin_core.compute_rsi")
@patch("modules.tibin_core.compute_macd")
@patch("modules.tibin_core.compute_bollinger")
def test_generate_signals_sell_trigger(mock_bollinger, mock_macd, mock_rsi):
    """Verify SELL signal when 2+ sell confirmations occur."""
    df = pd.DataFrame({"close": [100.0, 100.0, 100.0]})

    # Setup mock returns
    # 1. RSI sell: rsi > 65 (True)
    mock_rsi.return_value = pd.Series([70.0, 70.0, 70.0])

    # 2. MACD sell: macd < macd_signal & macd_hist < 0 (False)
    mock_macd.return_value = (
        pd.Series([2.0, 2.0, 2.0]),  # macd
        pd.Series([1.0, 1.0, 1.0]),  # macd_signal
        pd.Series([1.0, 1.0, 1.0])   # macd_hist
    )

    # 3. BB sell: close > bb_upper (True, meaning sell score = 2)
    mock_bollinger.return_value = (
        pd.Series([90.0, 90.0, 90.0]),  # bb_upper
        pd.Series([80.0, 80.0, 80.0]),  # bb_mid
        pd.Series([70.0, 70.0, 70.0])   # bb_lower
    )

    result = generate_signals(df)

    # sell_score = 1 (RSI) + 0 (MACD) + 1 (BB) = 2 -> SELL
    assert all(result["signal"] == "SELL")

@patch("modules.tibin_core.compute_rsi")
@patch("modules.tibin_core.compute_macd")
@patch("modules.tibin_core.compute_bollinger")
def test_generate_signals_hold_trigger(mock_bollinger, mock_macd, mock_rsi):
    """Verify HOLD signal when neither score is >= 2."""
    df = pd.DataFrame({"close": [100.0, 100.0, 100.0]})

    # Setup mock returns
    # 1. RSI buy: rsi < 35 (True)
    #    RSI sell: rsi > 65 (False)
    mock_rsi.return_value = pd.Series([30.0, 30.0, 30.0])

    # 2. MACD buy: macd > macd_signal & macd_hist > 0 (False)
    #    MACD sell: macd < macd_signal & macd_hist < 0 (True)
    mock_macd.return_value = (
        pd.Series([1.0, 1.0, 1.0]),  # macd
        pd.Series([2.0, 2.0, 2.0]),  # macd_signal
        pd.Series([-1.0, -1.0, -1.0])# macd_hist
    )

    # 3. BB buy: close < bb_lower (False)
    #    BB sell: close > bb_upper (False)
    mock_bollinger.return_value = (
        pd.Series([110.0, 110.0, 110.0]), # bb_upper
        pd.Series([100.0, 100.0, 100.0]), # bb_mid
        pd.Series([90.0, 90.0, 90.0])     # bb_lower
    )

    result = generate_signals(df)

    # buy_score = 1 (RSI) + 0 (MACD) + 0 (BB) = 1
    # sell_score = 0 (RSI) + 1 (MACD) + 0 (BB) = 1
    # Neither >= 2 -> HOLD
    assert all(result["signal"] == "HOLD")
