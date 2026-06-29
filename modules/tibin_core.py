#!/usr/bin/env python3
"""
tibin_core.py — TIBIN Terminal: Signal-to-Execution Pipeline
============================================================
Built by Jules (GCP VM agent) for Abdul's TIBIN trading terminal.

Components:
  1. OracleV5-style signal generator (RSI, MACD, Bollinger Bands)
  2. Order-flow calculator (Delta, Cumulative Volume Delta)
  3. Signal→Execution bridge (order-flow confirmation required)
  4. Paper trading logger (console + ~/tibin_trades.log)
  5. Live demo on synthetic BTC/USD data (1000 candles)

Run: python3 tibin_core.py
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOL = "BTC/USD"
N_CANDLES = 1000
LOG_FILE = Path(os.path.expanduser("~/tibin_trades.log"))
INITIAL_CAPITAL = 100_000.0  # USD

# ─────────────────────────────────────────────
# 1. Synthetic OHLCV Data Generator
# ─────────────────────────────────────────────

def generate_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Geometric Brownian Motion BTC/USD OHLCV, 1h candles."""
    np.random.seed(seed)
    start_price = 67_500.0
    mu = 0.0001   # slight upward drift
    sigma = 0.015 # 1.5% hourly vol

    prices = [start_price]
    for _ in range(n - 1):
        ret = np.random.normal(mu, sigma)
        prices.append(prices[-1] * np.exp(ret))

    prices = np.array(prices)
    noise = np.abs(np.random.normal(0, sigma * 0.3, (n, 4)))

    open_  = prices * (1 + noise[:, 0] * np.random.choice([-1, 1], n))
    close  = prices
    high   = np.maximum(open_, close) * (1 + noise[:, 1] * 0.5)
    low    = np.minimum(open_, close) * (1 - noise[:, 2] * 0.5)
    volume = np.abs(np.random.normal(500, 150, n))  # BTC volume

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(hours=i) for i in range(n)]

    df = pd.DataFrame({
        "timestamp": times,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })
    return df

# ─────────────────────────────────────────────
# 2. Technical Indicators (OracleV5-style)
# ─────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    res = 100 - (100 / (1 + rs))
    res.loc[(gain > 0) & (loss == 0)] = 100.0
    res.loc[(gain == 0) & (loss == 0)] = 50.0
    return res

def compute_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger(series: pd.Series, period=20, std_dev=2):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["close"]

    df["rsi"] = compute_rsi(close)
    df["macd"], df["macd_signal"], df["macd_hist"] = compute_macd(close)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = compute_bollinger(close)

    # Signal logic (Oracle V5 style: multi-confirmation)
    rsi_buy  = df["rsi"] < 35
    rsi_sell = df["rsi"] > 65
    macd_buy  = (df["macd"] > df["macd_signal"]) & (df["macd_hist"] > 0)
    macd_sell = (df["macd"] < df["macd_signal"]) & (df["macd_hist"] < 0)
    bb_buy   = close < df["bb_lower"]
    bb_sell  = close > df["bb_upper"]

    buy_score  = rsi_buy.astype(int) + macd_buy.astype(int) + bb_buy.astype(int)
    sell_score = rsi_sell.astype(int) + macd_sell.astype(int) + bb_sell.astype(int)

    # Need 2+ confirmations
    df["signal"] = "HOLD"
    df.loc[buy_score >= 2, "signal"] = "BUY"
    df.loc[sell_score >= 2, "signal"] = "SELL"

    return df

# ─────────────────────────────────────────────
# 3. Order-Flow Engine (order-flow-trader style)
# ─────────────────────────────────────────────

def compute_order_flow(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Simulate buy/sell volume from candle direction
    bullish = df["close"] > df["open"]
    df["buy_vol"]  = df["volume"] * np.where(bullish, 0.65, 0.35)
    df["sell_vol"] = df["volume"] * np.where(bullish, 0.35, 0.65)
    df["delta"]    = df["buy_vol"] - df["sell_vol"]
    df["cvd"]      = df["delta"].cumsum()
    # Normalise for signal confirmation
    df["delta_pct"] = df["delta"] / df["volume"]
    return df

# ─────────────────────────────────────────────
# 4. Signal→Execution Bridge + Paper Trading
# ─────────────────────────────────────────────

def run_paper_trading(df: pd.DataFrame) -> dict:
    log_lines = []
    trades = []
    capital = INITIAL_CAPITAL
    position = 0.0   # BTC held
    entry_price = 0.0
    wins = losses = 0

    for _, row in df.iterrows():
        sig = row["signal"]
        price = row["close"]
        delta_pct = row.get("delta_pct", 0)
        ts = row["timestamp"].strftime("%Y-%m-%d %H:%M")

        if sig == "BUY" and delta_pct > 0.05 and position == 0:
            # Buy: spend 10% of capital
            spend = capital * 0.10
            btc = spend / price
            position = btc
            entry_price = price
            capital -= spend
            reason = f"RSI/MACD/BB buy + delta={delta_pct:.2f}"
            log = f"{ts} | BUY  | {SYMBOL} | Price={price:,.0f} | BTC={btc:.4f} | Reason: {reason}"
            log_lines.append(log)
            trades.append({"ts": ts, "action": "BUY", "price": price})

        elif sig == "SELL" and delta_pct < -0.05 and position > 0:
            # Close position
            proceeds = position * price
            pnl = proceeds - (position * entry_price)
            capital += proceeds
            if pnl >= 0:
                wins += 1
            else:
                losses += 1
            reason = f"RSI/MACD/BB sell + delta={delta_pct:.2f} | P&L=${pnl:+,.2f}"
            log = f"{ts} | SELL | {SYMBOL} | Price={price:,.0f} | P&L=${pnl:+,.2f} | Reason: {reason}"
            log_lines.append(log)
            trades.append({"ts": ts, "action": "SELL", "price": price, "pnl": pnl})
            position = 0.0

    # Close any open position at last price
    if position > 0:
        last = df.iloc[-1]
        pnl = position * last["close"] - position * entry_price
        capital += position * last["close"]
        if pnl >= 0:
            wins += 1
        else:
            losses += 1
        ts_str = last['timestamp'].strftime('%Y-%m-%d %H:%M')
        log_lines.append(f"{ts_str} | CLOSE | {SYMBOL} | Force-close P&L=${pnl:+,.2f}")
        position = 0.0

    total_trades = wins + losses
    total_pnl = capital - INITIAL_CAPITAL
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    # Write log file
    LOG_FILE.write_text("\n".join(log_lines), encoding="utf-8")

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl_usd": total_pnl,
        "final_capital": capital,
        "log_lines": len(log_lines),
    }

# ─────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────

def main():
    print(f"TIBIN Core — {SYMBOL} | {N_CANDLES} candles | Paper trading")
    print("=" * 60)

    print("Generating synthetic OHLCV data...")
    df = generate_ohlcv(N_CANDLES)

    print("Computing indicators (RSI, MACD, Bollinger Bands)...")
    df = generate_signals(df)

    print("Computing order flow (Delta, CVD)...")
    df = compute_order_flow(df)

    signal_counts = df["signal"].value_counts().to_dict()
    buys = signal_counts.get('BUY', 0)
    sells = signal_counts.get('SELL', 0)
    holds = signal_counts.get('HOLD', 0)
    print(f"Signals: BUY={buys} SELL={sells} HOLD={holds}")

    print("Running paper trading engine...")
    results = run_paper_trading(df)

    print("\n" + "=" * 60)
    print("TIBIN CORE — FINAL RESULTS")
    print("=" * 60)
    for k, v in results.items():
        if k != "log_lines":
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")
    print(f"  trade_log: {LOG_FILE}")
    print("=" * 60)

    # Last 3 lines as required
    print(f"\nTotal Trades: {results['total_trades']}")
    print(f"Total P&L: ${results['total_pnl_usd']:+,.2f}")
    print(f"Win Rate: {results['win_rate']:.1f}%")

if __name__ == "__main__":
    main()
