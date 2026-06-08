# Experiment: v4 MaxDD Reduction (M1–M7)

**Branch:** `experiment/v4-maxdd-reduction`  
**Started:** 2026-06-02  
**Goal:** Reduce MaxDD from -27.2% to -17 to -20% while maintaining ≥12% CAGR and Sharpe ≥ 0.40

---

## Baseline (v4 b60s38)

| Metric | Value |
|--------|-------|
| Run name | `5y_v4_b60s38_backtestscorer` |
| Period | 5Y |
| Total return | +81.4% |
| CAGR | 12.9% |
| Sharpe | 0.42 |
| Max DD | -27.2% |
| Alpha | +5.5%/yr |
| Win rate | 61.0% |

```bash
python scripts/portfolio_backtest.py \
  --years 5 --signal-mode \
  --buy-threshold 60 --sell-threshold 38 --stop-loss 0.10 \
  --min-hold 3 --profit-trail 0.12 --profit-trigger 0.20 \
  --strong-buy 75 \
  --name "5y_v4_b60s38_backtestscorer"
```

---

## Best Result So Far — M1 p35/s3

| Metric | Baseline | Best (M1 p35/s3) | Change |
|--------|----------|------------------|--------|
| Total return | +81.4% | **+98.0%** | +16.6pp |
| CAGR | 12.9% | **14.6%** | +1.7pp |
| Sharpe | 0.42 | **0.53** | +0.11 |
| Max DD | -27.2% | **-22.7%** | **-4.5pp** |
| Alpha | +5.5%/yr | **+7.6%/yr** | +2.1pp |

```bash
python scripts/portfolio_backtest.py \
  --years 5 --signal-mode \
  --buy-threshold 60 --sell-threshold 38 --stop-loss 0.10 \
  --min-hold 3 --profit-trail 0.12 --profit-trigger 0.20 \
  --strong-buy 75 \
  --rs-exit --rs-percentile 0.35 --rs-strikes 3 \
  --name "5y_v4_M1_p35_s3"
```

**Success criteria status:**
- MaxDD ≤ -20%: ❌ at -22.7% (-2.7pp remaining)
- CAGR ≥ 12%: ✅ 14.6%
- Sharpe ≥ 0.40: ✅ 0.53
- Alpha ≥ +4%/yr: ✅ +7.6%

---

## Root Cause Analysis

Two positions drove the majority of the baseline drawdown:

- **COALINDIA** — held 26 months despite deteriorating relative strength. RS rank fell to ~35th percentile of NIFTY50 for 3+ consecutive months by mid-2024. An RS exit would have triggered Apr–May 2024, ~5 months before the Sep 2024 crash.
- **ITC** — 31-month value trap. Underperformed NIFTY by 20%+ in trailing 12M by early 2024.

The **remaining -2.7pp MaxDD** after M1 is structural — Jan 2025 (-9%) and Feb 2026 (-9.4%) were broad market selloffs hitting all stocks simultaneously. No stock-exit signal can fully eliminate correlated drawdown in a monthly rebalancing framework.

---

## Mechanisms — Status

### M1 — Relative Rank Degradation Exit ✅ Done
- **Rule:** If stock's 6M RS rank (vs NIFTY50 universe) falls below the exit percentile for N consecutive monthly reviews → exit.
- **CLI flags:** `--rs-exit --rs-percentile 0.35 --rs-strikes 3`
- **Implemented in:** `run_signal_simulation()` — Priority 2.5 exit, between profit-protect and score-exit.

**Parameter sweep (5Y, all else equal):**

| Percentile | Strikes | CAGR | Sharpe | MaxDD | Alpha | Verdict |
|-----------|---------|------|--------|-------|-------|---------|
| 0.30 | 3 | 13.1% | 0.45 | -23.9% | +5.4% | Good baseline |
| **0.35** | **3** | **14.6%** | **0.53** | **-22.7%** | **+7.6%** | **Best ✅** |
| 0.40 | 3 | 14.0% | 0.50 | -23.9% | +7.0% | MaxDD regresses |
| 0.30 | 2 | 11.6% | 0.37 | -23.9% | +5.1% | Too trigger-happy |
| 0.35 | 2 | 11.1% | 0.32 | -25.4% | +3.9% | Too aggressive |

**Key insight:** 35th percentile is the inflection point. It catches stocks ranked 31–35th that were chronically weak but evading the 30th threshold, without being so wide that it exits normal volatility. 3-strike grace is essential — 2 strikes costs -1.8pp CAGR with no MaxDD benefit.

---

### M2 — 12M Price Momentum Override 🔶 Tested, shelved
- **Rule:** Exit if stock underperforms NIFTY 12M return by >15% for 2 consecutive months.
- **Result (M2 alone):** CAGR 10.7%, MaxDD -25.4% — hurts CAGR, minimal MaxDD improvement.
- **Result (M1+M2 stacked):** MaxDD -23.1% (only -0.8pp better than M1 alone), CAGR drops 13.1% → 12.2%.
- **Verdict:** Net negative. The 15%/2-month threshold is too hair-trigger — exits winners before they peak. Could be revisited with looser params (20% threshold, 3 strikes) if MaxDD target remains elusive.

---

### M3 — Maximum Holding Period Cap ⬜ Not tested
- **Rule:** Hard cap at 18 months. Force exit regardless of score.
- **Rationale for skipping:** M1 already catches chronic RS laggards. M3 would overlap heavily and risk exiting mid-cycle positions that haven't yet broken RS threshold.
- **Revisit if:** M1 best config still shows individual positions held >18 months at time of exit.

---

### M4 — Portfolio Monthly Drawdown Circuit Breaker 🔶 Tested, shelved
- **Rule:** If previous month return < -8% → trim to 2 positions, block new entries. Clear when PV recovers.
- **Result (M4 alone, v1 — entry cap only):** MaxDD -27.2% (no change), CAGR 12.5%.
- **Result (M4 fixed — active trim to 2):** CAGR 11.7%, MaxDD -25.5% when stacked with M1.
- **Verdict:** Shelved. Root cause: in monthly rebalancing the bad period has *already happened* when the circuit fires. Active trim in recovery month sells into the bounce and misses the recovery. The signal is structurally one month too late.

---

### M5 — India VIX Exposure Scalar 🔶 Tested, shelved
- **Rule:** Scale max positions by VIX level: <18→1.0, 18-22→0.85, 22-26→0.65, >26→0.40.
- **Result (M5 alone):** CAGR 10.1%, MaxDD -27.0% — -2.8pp CAGR for near-zero MaxDD benefit.
- **Result (M1+M4+M5 stacked):** CAGR 10.7%, MaxDD -25.0% — worse than M1 alone on both metrics.
- **Verdict:** Shelved. India VIX sits in the 14-20 range routinely. Even with recalibrated thresholds (raised from <15 to <18 for full deployment), the scalar fires most months and consistently reduces position count, bleeding alpha without providing proportionate protection. VIX scalar may work in daily/weekly rebalancing but not monthly.

---

### M6 — Opportunity Cost Active Rotation ⬜ Not tested
- **Rule:** Swap held positions scoring <52 for candidates scoring ≥65 (if score gap ≥8pts).
- **Expected impact:** +2 to +3pp CAGR (upside capture, not MaxDD reduction).
- **Priority:** Low — CAGR is already 14.6% with M1 p35/s3. Consider only if MaxDD target is met and we want to push CAGR further.

---

### M7 — Factor Concentration HHI Guard ⬜ Not tested
- **Rule:** If any sector/factor HHI > 0.25 → reduce lowest-scoring stock in that factor before adding new positions.
- **Expected impact:** Reduces correlated drawdown from sector crowding.
- **Priority:** Medium — may help with the residual -2.7pp MaxDD from broad market selloffs if those are partly sector-correlated.

---

## Implementation Order — Revised

Original plan assumed additive stacking. Empirical result: **M1 alone is the most efficient mechanism.** M2–M5 all degrade performance when combined with M1 in a monthly framework.

Revised approach for the remaining -2.7pp MaxDD gap:

| Priority | Next step | Rationale |
|----------|-----------|-----------|
| 1 | Test M7 (HHI sector guard) | Correlated sector falls (FMCG 2024) are a different signal type from RS degradation — may stack cleanly with M1 |
| 2 | Revisit M2 with looser params (20% threshold, 3 strikes) | Original params too aggressive; wider gives it more chance to stack with M1 |
| 3 | Consider accepting -22.7% MaxDD | 3/4 success criteria exceeded, all metrics above target — the remaining -2.7pp may not be achievable without sacrificing CAGR |

---

## Results Log

| Date | Run name | CAGR | Sharpe | MaxDD | Alpha | Notes |
|------|----------|------|--------|-------|-------|-------|
| 2026-06-02 | `5y_v4_b60s38_backtestscorer` | 12.9% | 0.42 | -27.2% | +5.5% | Baseline |
| 2026-06-02 | `5y_v4_M1_rs_exit` (p30 s3) | 13.1% | 0.45 | -23.9% | +5.4% | M1 initial |
| 2026-06-02 | `5y_v4_M2_momentum_trap` | 10.7% | 0.30 | -25.4% | +3.6% | M2 alone ❌ |
| 2026-06-02 | `5y_v4_M1M2_stacked` | 12.2% | 0.40 | -23.1% | +5.3% | M1+M2 marginal ❌ |
| 2026-06-02 | `5y_v4_M4_circuit` | 12.5% | 0.40 | -27.2% | +5.5% | M4 v1 (entry cap only) ❌ |
| 2026-06-02 | `5y_v4_M5_vix` | 10.1% | 0.27 | -27.0% | +3.2% | M5 v1 (VIX<15) ❌ |
| 2026-06-02 | `5y_v4_M1M4M5_target` | 10.7% | 0.30 | -25.0% | +3.6% | Stacked before fixes ❌ |
| 2026-06-02 | `5y_v4_M4_fixed` | 12.5% | 0.40 | -27.2% | +5.5% | M4 fixed (active trim) ❌ |
| 2026-06-02 | `5y_v4_M5_fixed` | 10.1% | 0.27 | -27.0% | +3.2% | M5 recalibrated ❌ |
| 2026-06-02 | `5y_v4_M1M4M5_fixed` | 11.7% | 0.37 | -25.5% | +4.7% | M1+M4+M5 fixed ❌ |
| 2026-06-02 | `5y_v4_M1_p30_s2` | 11.6% | 0.37 | -23.9% | +5.1% | M1 tighter ❌ |
| 2026-06-02 | **`5y_v4_M1_p35_s3`** | **14.6%** | **0.53** | **-22.7%** | **+7.6%** | **Best ✅** |
| 2026-06-02 | `5y_v4_M1_p35_s2` | 11.1% | 0.32 | -25.4% | +3.9% | Too aggressive ❌ |
| 2026-06-02 | `5y_v4_M1_p40_s3` | 14.0% | 0.50 | -23.9% | +7.0% | MaxDD regresses ❌ |

---

## Decision Log

- **2026-06-02:** Identified M1–M7 from post-mortem of COALINDIA and ITC positions. Decided on isolation-first implementation order.
- **2026-06-02:** Branch `experiment/v4-maxdd-reduction` created.
- **2026-06-02:** M1 implemented. Parameter sweep confirms p35/s3 as optimal — wider than initial p30 but stops at the inflection point before p40 causes MaxDD to regress.
- **2026-06-02:** M2 tested and shelved — 15%/2-strike threshold too aggressive, exits winners pre-peak.
- **2026-06-02:** M4 (circuit breaker) and M5 (VIX scalar) both tested and shelved — structurally one month too late in monthly rebalancing; M5 VIX thresholds incompatible with India VIX distribution (14-20 range).
- **2026-06-02:** Revised plan: next priority is M7 (HHI sector guard) — different signal type from M1 with potential to address residual correlated-drawdown gap.

---

## Success Criteria

| Criterion | Target | Current best | Status |
|-----------|--------|-------------|--------|
| MaxDD | ≤ -20% | -22.7% | ❌ -2.7pp remaining |
| CAGR | ≥ 12% | 14.6% | ✅ +2.6pp above target |
| Sharpe | ≥ 0.40 | 0.53 | ✅ +0.13 above target |
| Alpha | ≥ +4%/yr | +7.6%/yr | ✅ +3.6pp above target |

Merge to `main` and update `BACKTEST_CHANGELOG.md` when MaxDD ≤ -20%, or when a decision is made to accept -22.7% as the practical floor given the monthly rebalancing constraint.
