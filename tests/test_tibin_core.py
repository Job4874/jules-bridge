"""Unit tests for modules/tibin_core.py."""

import unittest
import pandas as pd
import numpy as np
from modules.tibin_core import compute_macd

class TestComputeMACD(unittest.TestCase):
    def setUp(self):
        # Create a simple linear series for basic tests
        self.series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])

    def test_compute_macd_basic(self):
        macd, signal, hist = compute_macd(self.series)

        self.assertEqual(len(macd), len(self.series))
        self.assertEqual(len(signal), len(self.series))
        self.assertEqual(len(hist), len(self.series))

        # Checking if it computes without throwing errors and returns Series
        self.assertIsInstance(macd, pd.Series)
        self.assertIsInstance(signal, pd.Series)
        self.assertIsInstance(hist, pd.Series)

    def test_compute_macd_custom_params(self):
        macd, signal, hist = compute_macd(self.series, fast=5, slow=10, signal=3)

        # Ensure it works with custom parameters
        self.assertIsInstance(macd, pd.Series)
        self.assertIsInstance(signal, pd.Series)
        self.assertIsInstance(hist, pd.Series)

        macd_default, _, _ = compute_macd(self.series)
        # With different spans, the MACD values should be different
        self.assertFalse(macd.equals(macd_default))

    def test_compute_macd_empty_series(self):
        empty_series = pd.Series([], dtype=float)
        macd, signal, hist = compute_macd(empty_series)

        self.assertTrue(macd.empty)
        self.assertTrue(signal.empty)
        self.assertTrue(hist.empty)

    def test_compute_macd_constant_values(self):
        # If all values are the same, MACD should be 0 (ema_fast == ema_slow)
        constant_series = pd.Series([100.0] * 20)
        macd, signal, hist = compute_macd(constant_series)

        # MACD line should be exactly or essentially 0
        self.assertTrue(np.allclose(macd, 0.0))
        self.assertTrue(np.allclose(signal, 0.0))
        self.assertTrue(np.allclose(hist, 0.0))

if __name__ == '__main__':
    unittest.main()
