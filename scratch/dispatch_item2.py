"""dispatch_item2.py — dispatch TIBIN Core Integration to Jules VM."""
import requests, json

VM = "http://34.132.193.73:6000"
TOKEN = "JULES-VM-WORKER-999"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
P = {"http": None, "https": None}

TIBIN_TASK = """MISSION: Build TIBIN Core Integration — signal-to-execution pipeline.

CONTEXT:
- You are Jules, autonomous AI on GCP VM (Ubuntu 22.04, 4 vCPU, 15GB RAM)
- Abdul's Downloads has: TIBIN_CODEX_HANDOVER_BUNDLE.zip, OracleV5-main.zip, order-flow-trader-main.zip
- You cannot access his Windows machine Downloads directly
- Build from what you know about these systems from the codebase descriptions

TASK: Build a complete, working, self-contained Python trading signal pipeline that:

1. **Signal Generator** (OracleV5-style):
   - Generates BUY/SELL/HOLD signals based on: RSI, MACD, Bollinger Bands
   - Uses pandas + numpy (no external APIs needed for signals)
   - Works on OHLCV data (can use synthetic data for testing)

2. **Order-Flow Calculator** (order-flow-trader-style):
   - Calculates Delta (buy volume - sell volume)
   - Calculates Cumulative Volume Delta (CVD)
   - Identifies order flow imbalances

3. **Signal→Execution Bridge**:
   - Combines OracleV5 signal + order-flow confirmation
   - If signal=BUY AND delta>0: execute mock buy order
   - If signal=SELL AND delta<0: execute mock sell order
   - Otherwise: HOLD

4. **Paper Trading Logger**:
   - Logs every signal decision with timestamp, symbol, action, price, reason
   - Outputs to both console AND ~/tibin_trades.log

5. **Live Demo**:
   - Runs on synthetic BTC/USD tick data (1000 ticks)
   - Prints a summary: trades taken, P&L, win rate

REQUIREMENTS:
- Single self-contained Python file: ~/tibin_core.py
- Dependencies: pandas, numpy (pip installable in ~/venv)
- Must run to completion with: ~/venv/bin/python ~/tibin_core.py
- Output the final P&L and win rate as the last 3 lines

Write the COMPLETE working code. No placeholders. No TODOs. This must actually run."""

print("Dispatching TIBIN Core Integration task to Jules...")
r = requests.post(
    f"{VM}/task",
    json={"task": TIBIN_TASK, "task_type": "build", "context": "Build a real working trading pipeline — not a demo, not pseudocode"},
    headers=H, timeout=30, proxies=P
)
result = r.json()
print(f"Queued: {result}")
print("\nJules is building TIBIN Core. Check results in ~90s with:")
print("  python scratch\\get_results.py")
