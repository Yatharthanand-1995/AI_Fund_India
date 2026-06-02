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

Confirmed parameters:
```bash
python scripts/portfolio_backtest.py \
  --years 5 --signal-mode \
  --buy-threshold 60 --sell-threshold 38 --stop-loss 0.10 \
  --min-hold 3 --profit-trail 0.12 --profit-trigger 0.20 \
  --strong-buy 75 \
  --name "5y_v4_b60s38_backtestscorer"
```

---

## Root Cause Analysis

Two positions drove the majority of drawdown:

- **COALINDIA** — held 26 months despite deteriorating relative strength. RS rank fell to ~35th percentile of NIFTY50 for 3+ consecutive months by mid-2024. RS exit would have triggered Apr–May 2024, ~5 months before the Sep 2024 crash.
- **ITC** — 31-month value trap. Underperformed NIFTY by 20%+ in trailing 12M by early 2024. Two consecutive review cycles of underperformance should have triggered a 50% reduce, three → exit.

---

## The 7 Mechanisms (M1–M7)

### M1 — Relative Rank Degradation Exit
- **Problem:** COALINDIA held 26 months with RS deteriorating
- **Rule:** If stock's RS rank (vs NIFTY50 universe) falls below 30th percentile for 3 consecutive monthly reviews → exit
- **Expected MaxDD improvement:** -3 to -4pp
- **File:** `scripts/portfolio_backtest.py` — `run_signal_simulation()`
- **Status:** ✅ Implemented & tuned — best config: `--rs-percentile 0.35 --rs-strikes 3`
- **Tuning results:** p30/s3 → -23.9% (initial), **p35/s3 → -22.7%, CAGR 14.6%, Sharpe 0.53** (best)
- **Insight:** 35th percentile catches stocks ranked 31-35th that were chronically weak but evading the 30th threshold. 3-strike grace handles volatility — 2 strikes is too hair-trigger (-1.8pp CAGR cost).
- **M4/M5 verdict:** Both shelved. In monthly rebalancing, macro-timing mechanisms react *after* the loss is already realised. M4 circuit trims good holdings during the bad month then misses recovery. M5 VIX threshold too low for India (VIX typically 14-18) — fires almost every month, bleeding alpha without protection.

### M2 — 12M Price Momentum Override
- **Problem:** ITC value trap — fundamentals OK but price dead for 31 months
- **Rule:** If stock underperforms NIFTY total return by >15% over trailing 12M → watch list. Two consecutive reviews → reduce 50%. Three → exit.
- **Expected MaxDD improvement:** -2 to -3pp
- **File:** `scripts/portfolio_backtest.py`
- **Status:** ⬜ Not started

### M3 — Maximum Holding Period Cap
- **Problem:** Both COALINDIA and ITC
- **Rule:** Hard cap at 18 months (12M for positions below composite score 55). Force exit at cap regardless of score.
- **Expected MaxDD improvement:** Overlaps M1+M2 — marginal on its own
- **File:** `scripts/portfolio_backtest.py`
- **CLI flag:** `--max-hold 18`
- **Status:** ⬜ Not started

### M4 — Portfolio Monthly Drawdown Circuit Breaker
- **Problem:** Jan 2025 month saw -10.5% portfolio decline with no automatic response
- **Rule:** If portfolio drops >8% in a calendar month → reduce all positions to 50% target size. Restore when portfolio recovers to within 5% of the circuit level.
- **Expected MaxDD improvement:** -1 to -2pp
- **File:** `scripts/portfolio_backtest.py`
- **CLI flag:** `--monthly-dd-circuit 0.08`
- **Status:** ⬜ Not started

### M5 — India VIX Exposure Scalar
- **Problem:** 200-DMA is price-lagging. In Sep 2024, VIX spiked to 22+ before NIFTY broke 200-DMA — VIX would have signaled 2–3 weeks earlier.
- **Thresholds:**
  - VIX < 15 → full deployment (scalar = 1.0)
  - VIX 15–20 → scalar = 0.85
  - VIX 20–25 → scalar = 0.65
  - VIX > 25 → scalar = 0.40
- **Data source:** `^INDIAVIX` via yfinance
- **Expected MaxDD improvement:** -1 to -2pp
- **File:** `scripts/portfolio_backtest.py` — add `get_vix_scalar()` helper
- **Status:** ⬜ Not started

### M6 — Opportunity Cost Active Rotation
- **Problem:** Capital locked in stale/dead positions missed the 2024 rally
- **Rule:** Each monthly review — if a held position scores below 52 AND a non-held candidate scores ≥ 65 AND the candidate's score exceeds the held position's score by ≥ 8 pts → swap.
- **Expected impact:** +2 to +3pp CAGR (not MaxDD focused — upside capture)
- **File:** `scripts/portfolio_backtest.py`
- **Status:** ⬜ Not started

### M7 — Factor Concentration HHI Guard
- **Problem:** FMCG factor crowding (ITC + HINDUNILVR + NESTLEIND all fell together in 2024)
- **Rule:** Compute HHI across factor exposures (sector + style). If any factor HHI > 0.25 → reduce the lowest-scoring stock in that factor by 50% before adding new positions.
- **Expected MaxDD improvement:** Reduces correlated falls, unclear magnitude
- **File:** `scripts/portfolio_backtest.py`
- **Status:** ⬜ Not started

---

## Implementation Order

Run each mechanism isolated first (vs baseline), then stack:

| Step | Mechanisms | Run name pattern | Expected cumulative MaxDD |
|------|-----------|-----------------|--------------------------|
| 1 | M1 alone | `5y_v4_M1_rs_exit` | ~-23 to -24% |
| 2 | M1 + M2 | `5y_v4_M1M2_rs_momentum` | ~-21 to -22% |
| 3 | M1 + M2 + M3 | `5y_v4_M1M2M3_maxhold` | ~-20 to -21% |
| 4 | M1–M3 + M4 | `5y_v4_M1234_circuit` | ~-19 to -20% |
| 5 | M1–M4 + M5 | `5y_v4_M12345_vix` | ~-17 to -19% |
| 6 | M1–M5 + M6 | `5y_v4_M123456_rotation` | ~-17 to -19% + CAGR boost |
| 7 | All M1–M7 | `5y_v4_M1234567_full` | Target: -17 to -20% |

---

## Results Log

| Date | Run name | CAGR | Sharpe | MaxDD | Alpha | Notes |
|------|----------|------|--------|-------|-------|-------|
| 2026-06-02 | `5y_v4_b60s38_backtestscorer` *(baseline)* | 12.9% | 0.42 | -27.2% | +5.5% | v4 baseline |
| 2026-06-02 | `5y_v4_M1_rs_exit` (p30 s3) | 13.1% | 0.45 | -23.9% | +5.4% | M1 p30/s3 |
| 2026-06-02 | `5y_v4_M4_circuit` | 12.5% | 0.40 | -27.2% | +5.5% | M4 alone — no effect ❌ |
| 2026-06-02 | `5y_v4_M5_vix` | 10.1% | 0.27 | -27.0% | +3.2% | M5 alone — hurts CAGR ❌ |
| 2026-06-02 | `5y_v4_M1M4M5_fixed` | 11.7% | 0.37 | -25.5% | +4.7% | M4+M5 net negative vs M1 ❌ |
| 2026-06-02 | `5y_v4_M1_p30_s2` | 11.6% | 0.37 | -23.9% | +5.1% | Too trigger-happy ❌ |
| 2026-06-02 | **`5y_v4_M1_p35_s3`** | **14.6%** | **0.53** | **-22.7%** | **+7.6%** | **Best config ✅** |
| 2026-06-02 | `5y_v4_M1_p35_s2` | 11.1% | 0.32 | -25.4% | +3.9% | Too aggressive ❌ |

---

## Decision Log

- **2026-06-02:** Identified M1–M7 from post-mortem of COALINDIA and ITC positions. Decided to implement in isolation-first order to isolate each mechanism's contribution before stacking.
- **2026-06-02:** Branch `experiment/v4-maxdd-reduction` created. All M1–M7 changes to `portfolio_backtest.py` will land here, not on `main`, until the full stack is validated.

---

## Success Criteria

- MaxDD ≤ -20% on 5Y backtest
- CAGR ≥ 12% (must not regress from baseline)
- Sharpe ≥ 0.40
- Alpha ≥ +4%/yr

If all four criteria are met on `5y_v4_M1234567_full`, merge to `main` and update `BACKTEST_CHANGELOG.md`.
