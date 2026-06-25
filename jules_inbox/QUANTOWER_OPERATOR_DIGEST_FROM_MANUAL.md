# Quantower Operator Digest — For Jules (read before UI)

**Source:** Operator-provided *Quantower & Visual Studio Master Manual* (Ch 1–14 + Tradeify recovery doc).  
**Full text:** `QUANTOWER_VISUAL_STUDIO_MASTER_MANUAL.md`  
**This file:** Actionable rules only. Do not trade until you have read both.

---

## A. Mode map (operator ground truth — overrides guessing)

| UI / action | Mode | Your job |
|-------------|------|----------|
| **Strategy Manager (StM)** | **Live / paper / demo runtime** | Run strategy instance, real connections, logs, telemetry, DOM/L2 live |
| **Backtest & Optimize panel** | **Historical simulation** | Tick/OHLC backtest, optimization — **not** live proof |
| **Market Replay chart** | **Replay runtime** | Same strategy code path as live feed; not the optimizer UI |
| **Reload / restart Quantower** | **Logout + reconnect** | Avoid unless operator explicitly approves |
| **Visual Studio “Quantower Algo” debug attached to Backtest** | **Debug backtest session** | Different from StM Run — know which panel VS attached to |

**Never** open Backtest when the task says StM/live/replay. **Never** claim DOM/MBO edge from M1-only backtest.

---

## B. Path truth on THIS host (manual vs reality)

The manual describes default install under `%LocalAppData%\Quantower`. **This operator uses:**

| Manual says | This host uses |
|-------------|----------------|
| `%LocalAppData%\Quantower\Algo` | `C:\Quantower\Settings\Scripts\Strategies\` (deploy target) |
| Generic Settings | `C:\Quantower\Settings\settings.xml` |
| Platform binaries | `C:\Quantower\TradingPlatform\v1.146.13\` |
| Strategy instances | `C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 ({guid})\info.xml` |

**Canonical Oracle build:** `C:\aotp\projects\OracleV5` — branch `perf/fix-empty-catch-block-datafeedmanager`.

**Active instance (use this one — do not spawn duplicates):**

`Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml`

---

## C. Connections (before Run in StM)

### CQG / AMP (demo first)

1. Connection Manager → CQG → Demo credentials (CQG login, not broker portal login).
2. Enable exchanges (CME, etc.) in connection gear → Exchanges.
3. Title bar must show **Connected** — screenshot proof required.
4. **Connection limit:** same CQG user cannot be logged in elsewhere (TradingView, etc.).

### Rithmic (Tradeify / paper)

Manual recommends **R|Trader Pro Plugin Mode**:

1. R|Trader Pro: Allow Plugins = ON → login (e.g. Rithmic Paper Chicago).
2. Quantower Rithmic settings: **Use RTrader (Plugin Mode)** = ON, same server.
3. Do **not** open a second direct Rithmic session (double fees / login errors).
4. **MBO:** enable in Rithmic connection settings if strategy needs queue-level book; DOM Trader → MBO column coloring.

### Oracle binding rules (from manual + Oracle code)

- Symbol and Account must share **same ConnectionId**.
- Use **Micro (MES/MNQ)** for drawdown-constrained recovery — not Minis unless operator approves.
- **Never** hold Minis and Micros simultaneously (Tradeify mixing rule applies to funded accounts).

---

## D. Strategy Manager workflow (live path)

From manual Ch 8 + operator feedback:

1. Screenshot: connection status + confirm Quantower **not** restarted this session.
2. Open **StM** (toolbar **StM** button on this host — do not hunt menus blindly).
3. **One** Oracle V5 instance — do not click **+** repeatedly (creates empty `ScriptsData` folders without `info.xml`).
4. Configure **Symbol** + **Account** in instance settings (gear) — screenshot settings.
5. Shell-first: `Deploy` → `Apply-OracleReplayProfile.ps1` → `Verify-OracleReplayReady.ps1`.
6. Click **Run** only after symbol/account set — Run creates/updates `info.xml`.
7. Monitor **Logs** and **Metrics** panes in StM (manual Ch 8).
8. Collect telemetry CSV under operator OneDrive path when gates pass.

**OnStop hygiene (manual Ch 12):** unsubscribe `NewQuote`, `NewLast`, `NewLevel2` — Oracle must not leak subscriptions.

---

## E. Backtest workflow (separate path)

From manual Ch 8 + Ch 13:

1. Open **Backtest & Optimize** panel (not StM).
2. Select strategy, symbol, date range.
3. **History type:** DOM/tape strategies need **tick** history — M1 alone is `BAR_MODEL_ONLY`.
4. Set commissions, slippage (1–2 ticks conservative).
5. VS debug: General Settings → Algo → **Allow connection from Visual Studio** (port ~31550).
6. Attach VS debugger to **Backtest** session when debugging — not the same as StM Run.

Label results: `BAR_MODEL_ONLY` / `TICK_MODEL` / `NOT_LIVE_CERTIFIED`.

---

## F. Visual Studio (manual Ch 9–13)

1. VS 2022 + **.NET desktop development** workload.
2. Quantower Algo extension → link to `C:\Quantower\TradingPlatform`.
3. Reference `TradingPlatform.BusinessLayer.dll` from **v1.146.13** on this host.
4. Build Release x64 → `Deploy-OracleQuantowerStrategy.ps1`.
5. Prefer **shell verify** over UI when possible.

**Debugging:** Breakpoints in `OnRun`, event handlers, `PlaceOrder` — inspect ConnectionId, symbol/account IDs, order result.

---

## G. Data / analytics Oracle may use (manual Ch 6–7)

Know what each requires:

| Feature | Needs |
|---------|--------|
| DOM / multi-level book | Level 2 / MBO subscription, fresh timestamps |
| Footprint / clusters | Volume analysis finished — not loading as zero |
| CVD / delta | Aggressor-classified tape |
| Volume profile / POC | Trade history for session |
| VWAP | Defined session anchor — know Oracle’s formula |
| Bar backtest | Does **not** reproduce full book dynamics |

Stale L2 or unfinished volume analysis = **veto**, not zero.

---

## H. Tradeify / funded constraints (if EnableLiveTrading ever true)

From operator Tradeify doc — Oracle risk gates should enforce:

- Hard stop below trailing floor — do not rely on DLL alone when drawdown buffer is small.
- Daily profit cap / consistency rule — avoid one huge day trapping payout math.
- Min hold **> 10 seconds** on majority of trades (micro-scalping audit).
- No mini/micro mixing; no hedging across accounts.
- Static IP VPS for algo — no VPN login weirdness on dashboard.
- Flatten and **disable algo** during payout review window.

**Funded account is NOT first test environment** — AMP/CQG demo first.

---

## I. Research protocol (operator: “smart child”)

Before any **new** UI click path:

1. Read relevant manual chapter section (cite chapter in `JULES_RESPONSE.md`).
2. If YouTube referenced — summarize transcript bullets first.
3. Screenshot → one action → screenshot → write result.
4. Two failures → stop UI; shell-only + ask operator.

---

## J. Verification commands (shell — prefer over UI)

```powershell
cd C:\aotp\projects\OracleV5
dotnet build OracleV5.Strategy\OracleV5.Strategy.csproj -c Release -a x64
powershell -ExecutionPolicy Bypass -File .\Tools\Deploy-OracleQuantowerStrategy.ps1
powershell -ExecutionPolicy Bypass -File .\Tools\Apply-OracleReplayProfile.ps1 -InfoXmlPath "C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5 (f9eb0699-4c73-4ee2-b377-87c92468b6c7)\info.xml"
powershell -ExecutionPolicy Bypass -File .\Tools\Verify-OracleReplayReady.ps1
```

Pass **all** verify checks + fresh telemetry before claiming replay-ready.

---

## K. Session report template (mandatory)

See `JULES_MASTER_PROMPT_QUANTOWER_OPERATOR.md` §8.

---

*Digest version 1 — 2026-06-25. Update when operator supplies revised manual pages.*
