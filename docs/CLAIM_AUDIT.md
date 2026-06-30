# CLAIM_AUDIT — Oracle V5 Eight-Target Verification

> **Audience:** Global Verdent Rule / Oracle V5 Advanced Operator  
> **Started:** 2026-06-26  
> **Source repo:** `C:\aotp\projects\OracleV5`  
> **Strategy version (constants):** `5.0.25-duplicate-guard` (`OracleConstants.StrategyVersion`)

Status legend:

| Status | Meaning |
| --- | --- |
| `VERIFIED_SOURCE` | Confirmed in OracleV5 source code at cited path |
| `PENDING_RUNTIME` | Source confirmed; live Quantower / telemetry / bridge evidence not yet collected this audit cycle |
| `MISMATCH` | Source vs deployed instance disagree — needs operator resolution |
| `UNVERIFIED` | Claim not yet located in source |

---

## Audit Summary

| # | Target | Status | Last checked |
| --- | --- | --- | --- |
| 1 | Penalty weights (19 GodScore weights sum = 1.0) | `VERIFIED_SOURCE` | 2026-06-26 |
| 2 | Kelly breakpoints | `VERIFIED_SOURCE` | 2026-06-26 |
| 3 | GodScore factor count | `VERIFIED_SOURCE` | 2026-06-26 |
| 4 | Pipeline trail (`pipeline_trace`) | `VERIFIED_SOURCE` / `PENDING_RUNTIME` | 2026-06-26 |
| 5 | Direction conflict penalty | `VERIFIED_SOURCE` | 2026-06-26 |
| 6 | Break-even offset | `VERIFIED_SOURCE` | 2026-06-26 |
| 7 | Fill / pending order timeout | `VERIFIED_SOURCE` | 2026-06-26 |
| 8 | Apex warn-buffer (drawdown warning utilization) | `VERIFIED_SOURCE` | 2026-06-26 |

**Overall:** 8/8 targets located in source. **0/8** fully closed with live runtime telemetry in this Jules repo session.

---

## Target 1 — Penalty Weights (GodScore factor weights)

**Claim:** Nineteen configurable GodScore factor weights exist and must sum to `1.0`.

**Source of truth:**

- `OracleV5.Strategy/OracleStrategy_Part1_Config.cs` — `WeightVpin` through `WeightOptions` (19 inputs)
- Validation: `ValidateGodScoreWeights()` rejects if sum ≠ 1.0 (error message references sum)

**Verified values (defaults):**

| Factor | Weight |
| --- | ---: |
| VPIN | 0.10 |
| Regime | 0.08 |
| Volatility | 0.07 |
| Structure | 0.08 |
| Liquidity | 0.06 |
| FVG | 0.05 |
| Microstructure | 0.08 |
| Auction | 0.05 |
| Session | 0.04 |
| Correlation | 0.05 |
| Macro | 0.06 |
| VIX | 0.05 |
| Breadth | 0.04 |
| Seasonality | 0.03 |
| Setup Quality | 0.05 |
| Wyckoff | 0.03 |
| Day Type | 0.03 |
| Expiry | 0.02 |
| Options Flow | 0.03 |
| **Sum** | **1.00** |

**Post-normalization penalties (separate from weights):**

- `OracleConstants.GodScore.LowCoveragePenalty` = `1.00`
- `OracleConstants.Expiry.MaxGodScorePenaltyPoints` = `1.50`
- Expiry roll penalties: `0.35` / `0.55` / `0.85` / `1.00` / `0.40` by phase

**Runtime check:** Compare live `info.xml` strategy settings against defaults if instance was customized.

**Status:** `VERIFIED_SOURCE`

---

## Target 2 — Kelly Breakpoints

**Claim:** Kelly sizing uses explicit statistical gates and fractional Kelly for production safety.

**Source of truth:** `OracleV5.Strategy/Risk/KellyCalculator.cs`

| Breakpoint | Value | Behavior |
| --- | --- | --- |
| Invalid input | — | `ReasonCode = KELLY_INVALID_INPUT`, not ready |
| Insufficient stats | `trades <= 0` or non-positive avg win/loss | `KELLY_INSUFFICIENT_STATS` |
| Raw Kelly formula | `(b*p - q) / b` | Standard Kelly |
| Max allowance cap | `input.MaxAllowance` (default `1.0`) | Caps raw Kelly |
| **Fractional Kelly** | **`× 0.25`** | `recommended = capped * 0.25` |
| Ready | — | `ReasonCode = KELLY_READY` |

**Status:** `VERIFIED_SOURCE`

---

## Target 3 — GodScore Factor Count

**Claim:** GodScore v3 is a **19-factor** composite on a **0–20** scale.

**Source of truth:**

- `OracleConstants.GodScore.ExpectedFactorCount` = **19**
- `OracleConstants.GodScore.MinimumAvailableFactors` = **8**
- `OracleStrategy_Part14_GodScore.cs` header documents 19-factor model
- `OracleConstants.GodScore.MaxScore` = **20.0**

**Threshold constants:**

| Constant | Value |
| --- | ---: |
| ScalpThreshold / ENTRY_MIN_SCORE | 12.0 |
| SwingThreshold / SWING_MIN_SCORE | 14.0 |
| AssassinThreshold | 18.0 |

**Configured input thresholds (normalized at runtime):**

- `MinGodScoreToOpen` default `0.60` → scales to ~12.0 on 20-pt scale
- Deploy scripts often write `11.15` / `11.75` / `5.50` to Quantower `info.xml`

**Runtime check:** Read active instance `info.xml` GodScore Min To Open/Add/Flatten.

**Status:** `VERIFIED_SOURCE` (count/thresholds); deployed instance values `PENDING_RUNTIME`

---

## Target 4 — Pipeline Trail

**Claim:** Master pipeline stages emit forensic `pipeline_trace` CSV rows.

**Source of truth:**

- `Observability/CsvTelemetryService.cs` — channel `pipeline_trace`, schema `timestamp,stage,pass_fail,reason,payload_summary`
- Emitters include: `OracleStrategy_Part2_Lifecycle.cs` (STARTUP), `Part13_Management.cs` (GODSCORE, EXECUTION, RISK), `Part15_QuantowerSelector.cs` (SELECTOR), `ForensicTelemetryHub.cs`

**Example stages observed in source:** `STARTUP`, `SYMBOL`, `SELECTOR`, `GODSCORE`, `EXECUTION`, `RISK`, `TELEMETRY`

**Runtime check:** Confirm row in `OneDrive\Documents\Oracle_V5_Telemetry\CSV\pipeline_trace*.csv` after strategy run.

**Status:** `VERIFIED_SOURCE` · telemetry file presence `PENDING_RUNTIME`

---

## Target 5 — Direction Conflict Penalty

**Claim:** Conflicting directional conviction applies a fixed GodScore penalty.

**Source of truth:** `OracleConstants.GodScore`

| Constant | Value |
| --- | ---: |
| `DirectionConflictPenalty` | **0.75** |
| `MinDirectionalConviction` | **0.15** |

**Status:** `VERIFIED_SOURCE`

---

## Target 6 — Break-Even

**Claim:** Break-even migration moves stop with configurable tick offset.

**Source of truth:**

- `OracleStrategy_Part1_5_RuntimeState.cs` — `BreakEvenOffsetTicks` default **2**
- `OracleStrategy_Part13_Management.cs` — `GetBreakEvenOffsetTicks()` fallback **1.0** if config missing
- Management handler: `HandleBreakEvenMigration()` tags stop modify reason `BREAK_EVEN`

**Status:** `VERIFIED_SOURCE`

---

## Target 7 — Fill Timeout

**Claim:** Pending orders expire after a bounded timeout.

**Source of truth:** `OracleStrategy_Part16_Execution.cs`

| Constant | Value |
| --- | ---: |
| `_pendingOrderTimeout` | **20 seconds** |
| `_executionLockTimeout` | **30 seconds** |
| Accessor | `GetPendingOrderTimeout()` returns `_pendingOrderTimeout` |

**Related:** `Execution/FillTracker.cs` — `IsOrderFilled(requestId)` for fill tracking.

**Runtime check:** Observe order cancel/reject in telemetry or logs when fill not received within 20s.

**Status:** `VERIFIED_SOURCE` · live fill behavior `PENDING_RUNTIME`

---

## Target 8 — Apex Warn-Buffer

**Claim:** Account drawdown guard warns before hard lock — prop-firm style utilization buffer.

**Primary mapping (source):**

| Constant | Location | Value |
| --- | --- | ---: |
| `Risk.WarningUtilization` | `OracleConstants.cs` | **0.80** (80%) |
| `DrawdownMonitor` private const | `Risk/DrawdownMonitor.cs` | **0.80** |
| Size at warning | `Risk.SizeWarning` | **0.50** |
| Size locked | `Risk.SizeLocked` | **0.00** |

**Related Assassin trail buffer (profit lock, not warn utilization):**

| Constant | Value |
| --- | ---: |
| `AccountGuard.AssassinTrailBuffer` | **700.00** USD |
| `AccountGuard.AssassinActivationProfit` | **1000.00** USD |
| `AccountGuard.AssassinInitialLockProfit` | **300.00** USD |

**Note:** "Apex" in codebase comments (`Part5_Correlation.cs`) refers to hardened production path, not a separate Apex prop-firm module. Warn-buffer audit target maps to **80% utilization warning** unless operator spec defines otherwise.

**Status:** `VERIFIED_SOURCE`

---

## Verification Commands (next session)

```powershell
# Source re-verify (from OracleV5 repo)
Select-String -Path "C:\aotp\projects\OracleV5\OracleV5.Strategy\Utilities\OracleConstants.cs" -Pattern "ExpectedFactorCount|DirectionConflictPenalty|WarningUtilization"

# Live instance GodScore thresholds
# Replace with active info.xml from memory/quantower.md
Select-String -Path "C:\Quantower\Settings\Scripts\ScriptsData\Oracle V5*\info.xml" -Pattern "GodScore Min"

# Bridge oracle status (requires fresh evidence)
curl http://127.0.0.1:5000/oracle/status

# Telemetry pipeline trail
Get-ChildItem "$env:USERPROFILE\OneDrive\Documents\Oracle_V5_Telemetry\CSV\pipeline_trace*"
```

---

## Audit Log

| Date | Agent action | Result |
|---|---|---|
| 2026-06-26 | Initial audit — source read of OracleV5 constants, Kelly, execution, telemetry | 8/8 targets located; runtime pass deferred |

---

## Update Rule

When a target moves to full verification:

1. Add evidence path (file hash, CSV row sample, or `/oracle/status` timestamp)
2. Change status from `PENDING_RUNTIME` to `VERIFIED_RUNTIME`
3. Update `PROJECT_STATE.md` blocking issue B2 if evidence gate cleared
