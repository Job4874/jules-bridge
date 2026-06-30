"""dispatch_write_and_run.py — tell Jules to write tibin_core.py to disk and run it."""
import requests

VM = "http://34.132.193.73:6000"
H = {"Authorization": "Bearer JULES-VM-WORKER-999"}
P = {"http": None, "https": None}

# Tell Jules to write the tibin core script and run it
TASK = """Write the complete tibin_core.py trading pipeline to ~/tibin_core.py on this VM, then run it.

The script must:
1. Generate 1000 synthetic BTC/USD OHLCV candles
2. Compute RSI (14), MACD (12/26/9), Bollinger Bands (20,2)
3. Generate BUY/SELL/HOLD signals
4. Compute order-flow Delta and Cumulative Volume Delta (CVD)
5. Execute mock trades (BUY when signal=BUY and delta>0, SELL when signal=SELL and delta<0)
6. Log every trade with timestamp, price, action, reason to ~/tibin_trades.log
7. Print final 3-line summary: total_trades, pnl, win_rate

Write it as a shell task in two steps:
Step 1: Write the Python file using heredoc or Python -c
Step 2: Run it with ~/venv/bin/pip install pandas numpy --quiet && ~/venv/bin/python ~/tibin_core.py

Return the last 10 lines of output (the trade log summary).

Important: write WORKING code. The script must actually execute and print results."""

r = requests.post(f"{VM}/task",
    json={"task": TASK, "task_type": "shell"},
    headers=H, timeout=30, proxies=P)
print(f"Queued: {r.json()}")
print("Jules is writing and running tibin_core.py on the VM. Check results in 120s.")
