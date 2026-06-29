import pytest
import pandas as pd
import numpy as np

from modules.tibin_core import compute_bollinger

def test_compute_bollinger_happy_path():
    """Test compute_bollinger with normal inputs."""
    data = [10, 12, 11, 14, 15, 13, 16, 18, 17, 19]
    series = pd.Series(data)

    # Use a small period for testing
    period = 3
    upper, sma, lower = compute_bollinger(series, period=period, std_dev=2)

    # Assert return types
    assert isinstance(upper, pd.Series)
    assert isinstance(sma, pd.Series)
    assert isinstance(lower, pd.Series)

    # Assert lengths
    assert len(upper) == len(series)
    assert len(sma) == len(series)
    assert len(lower) == len(series)

    # First (period - 1) elements should be NaN
    assert pd.isna(sma.iloc[0:period - 1]).all()
    assert pd.isna(upper.iloc[0:period - 1]).all()
    assert pd.isna(lower.iloc[0:period - 1]).all()

    # Calculate expected for the third element manually
    # data[0:3] = [10, 12, 11]
    expected_sma_2 = np.mean([10, 12, 11])
    expected_std_2 = np.std([10, 12, 11], ddof=1) # pandas uses sample std (ddof=1) by default

    # Floating point comparison
    np.testing.assert_almost_equal(sma.iloc[2], expected_sma_2)
    np.testing.assert_almost_equal(upper.iloc[2], expected_sma_2 + 2 * expected_std_2)
    np.testing.assert_almost_equal(lower.iloc[2], expected_sma_2 - 2 * expected_std_2)

def test_compute_bollinger_short_series():
    """Test compute_bollinger when the series is shorter than the period."""
    series = pd.Series([10, 12, 11])
    period = 5

    upper, sma, lower = compute_bollinger(series, period=period)

    # Everything should be NaN
    assert pd.isna(sma).all()
    assert pd.isna(upper).all()
    assert pd.isna(lower).all()

def test_compute_bollinger_constant_series():
    """Test compute_bollinger with a constant series where std_dev will be 0."""
    series = pd.Series([10, 10, 10, 10, 10])
    period = 3

    upper, sma, lower = compute_bollinger(series, period=period, std_dev=2)

    # For valid rolling windows, upper == sma == lower since std is 0
    # First 2 elements are NaN
    assert pd.isna(sma.iloc[0:2]).all()

    # Elements from index 2 onwards should be exactly 10
    assert (sma.iloc[2:] == 10).all()
    assert (upper.iloc[2:] == 10).all()
    assert (lower.iloc[2:] == 10).all()
