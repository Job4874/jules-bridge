```python
#!/usr/bin/env python3
"""
tibin_core.py
Complete signal-to-execution pipeline:
 - OracleV5-style signal generator (RSI, MACD, Bollinger Bands)
 - Order‑flow calculator (Delta, CVD)
 - Signal→Execution bridge (requires order‑flow confirmation)
 - Paper trading logger (console + ~/tibin_trades.log)
 - Live demo on synthetic BTC/USD tick data (1000 ticks)
Prints final P&L and win rate as the last three lines.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------
# Configuration
# ---------------------------
SYMBOL = "BTC/USD"
TICKS = 1000
LOG_FILE = os.path.expanduser("~/tibin_trades.log")
INITIAL_CAPITAL = 0.0  # we track P&L in price units, not cash

# ---------------------------
# Helper: Synthetic OHLCV data
# ---------------------------
def generate_synthetic_ohlcv(n: int) -> pd.DataFrame:
    """Generate realistic OHLCV tick data for BTC/USD."""
    np.random.seed(42)
    # start price arou