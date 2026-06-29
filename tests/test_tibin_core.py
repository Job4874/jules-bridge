import numpy as np
import pandas as pd
import pytest

from modules.tibin_core import compute_order_flow

def test_compute_order_flow_bullish_and_bearish():
    df = pd.DataFrame({
        "open": [100, 100],
        "close": [110, 90],
        "volume": [100, 100]
    })

    result = compute_order_flow(df)

    # Row 0: bullish (close > open)
    # buy_vol = 100 * 0.65 = 65
    # sell_vol = 100 * 0.35 = 35
    # delta = 65 - 35 = 30
    assert result.loc[0, "buy_vol"] == pytest.approx(65.0)
    assert result.loc[0, "sell_vol"] == pytest.approx(35.0)
    assert result.loc[0, "delta"] == pytest.approx(30.0)
    assert result.loc[0, "delta_pct"] == pytest.approx(30.0 / 100.0)

    # Row 1: bearish (close <= open)
    # buy_vol = 100 * 0.35 = 35
    # sell_vol = 100 * 0.65 = 65
    # delta = 35 - 65 = -30
    assert result.loc[1, "buy_vol"] == pytest.approx(35.0)
    assert result.loc[1, "sell_vol"] == pytest.approx(65.0)
    assert result.loc[1, "delta"] == pytest.approx(-30.0)
    assert result.loc[1, "delta_pct"] == pytest.approx(-30.0 / 100.0)

def test_compute_order_flow_cvd_calculation():
    df = pd.DataFrame({
        "open": [100, 100, 100],
        "close": [110, 90, 110],
        "volume": [100, 100, 100]
    })

    result = compute_order_flow(df)

    # delta values: [30, -30, 30]
    # cvd values: [30, 0, 30]
    assert result.loc[0, "cvd"] == pytest.approx(30.0)
    assert result.loc[1, "cvd"] == pytest.approx(0.0)
    assert result.loc[2, "cvd"] == pytest.approx(30.0)

def test_compute_order_flow_zero_volume():
    df = pd.DataFrame({
        "open": [100],
        "close": [110],
        "volume": [0]
    })

    result = compute_order_flow(df)

    assert result.loc[0, "buy_vol"] == pytest.approx(0.0)
    assert result.loc[0, "sell_vol"] == pytest.approx(0.0)
    assert result.loc[0, "delta"] == pytest.approx(0.0)
    assert result.loc[0, "cvd"] == pytest.approx(0.0)
    assert np.isnan(result.loc[0, "delta_pct"])

def test_compute_order_flow_missing_columns():
    df = pd.DataFrame({
        "open": [100],
        "close": [110]
        # missing 'volume'
    })

    with pytest.raises(KeyError):
        compute_order_flow(df)

def test_compute_order_flow_does_not_modify_original():
    df = pd.DataFrame({
        "open": [100],
        "close": [110],
        "volume": [100]
    })

    original_columns = df.columns.tolist()
    _ = compute_order_flow(df)

    # Original dataframe should not have new columns
    assert df.columns.tolist() == original_columns
