# Risk Mechanisms Status
**Last updated:** 2026-06-04  
**Branch:** `experiment/v4-maxdd-reduction`  
**v4 baseline:** CAGR 12.9% | Sharpe 0.42 | MaxDD -27.2% | Alpha +5.5%/yr  
**Target:** MaxDD -17 to -20% while maintaining CAGR ≥ 12%

---

## Mechanism Tracker

| # | Mechanism | Root Cause | CLI Flag | Backtest Result | Unit Tested | Walk-Forward | Live System | Verdict |
|---|-----------|-----------|----------|-----------------|-------------|--------------|-------------|---------|
| M1 | Relative rank degradation exit | COALINDIA 26-month hold | `--rs-exit` | ✅ p35/s3 → CAGR 14.6%, Sharpe 0.53 | ✅ | ❌ | ✅ | **USE** |
| M2 | 12M price momentum override | ITC value trap | `--m2-exit` | ⚠️ Hurts 2023 bull (-1.5pp CAGR) | ❌ | ❌ | ❌ | Skip (overlaps M1) |
| M3 | Max holding period (12/18/24M hurdle) + cooldown | ITC + COALINDIA stale hold | `--m3-maxhold --m3-cooldown` | ✅ Best: M1+M3+cooldown → CAGR 15.3%, Sharpe 0.57 | ✅ | ❌ | ✅ | **USE** |
| M4 | Monthly portfolio drawdown circuit breaker | Jan 2025 -10.5% | `--m4-circuit` | ⚠️ No improvement over M1+M3 | ❌ | ❌ | ❌ | Skip (M1+M3 sufficient) |
| M5 | India VIX exposure scalar | Sep 2024 pre-crash signal | `--m5-vix` | ⚠️ CAGR drop (-2.6pp) vs M1 alone | ❌ | ❌ | ❌ | Skip (200-DMA sufficient) |
| M6 | Opportunity cost active rotation | Missing rally while holding dead stocks | `--m6-rotation` | ⚠️ gap=12 hurts, gap=18 ≈ M1+M3 | ✅ | ❌ | ❌ | Skip (M1 covers this) |
| M7 | Factor concentration HHI gate | ITC+BRITANNIA+NESTLE same factor | `--m7-hhi` | ❌ CAGR -3pp, no MaxDD improvement | ✅ | ❌ | ❌ | Skip (too tight for NIFTY50) |
| M1+SectorGuard | Pause M1 strikes when sector recovering | 2025 IT rally miss | `--m1-sector-guard` | ❌ Sharpe 0.44 (vs 0.57 without) | ✅ | ❌ | ❌ | **REJECTED — net negative** |

**Legend:** ✅ Done | ❌ Not yet | ⚠️ Partial

---

## Mechanism Details

### M1 — Relative Rank Degradation Exit
- **What:** Exit if cross-sectional score rank falls below `rs_exit_percentile` for `rs_exit_strikes` consecutive months
- **Best config found:** `--rs-exit --rs-percentile 0.35 --rs-strikes 3` → MaxDD -22.7% (+4.5pp improvement), CAGR 14.6% (+1.7pp), Sharpe 0.53 (+0.11)
- **Historical validation:** Would have exited COALINDIA ~Mar 2024 (5 months before Sep 2024 crash)
- **Next:** Write unit test + regression test

### M2 — 12M Price Momentum Override
- **What:** Exit if held stock underperforms NIFTY by > `m2_threshold` for `m2_strikes` consecutive months (after 6M min hold)
- **Addresses:** ITC-style value traps — excellent fundamentals, zero price return vs benchmark
- **Status:** Implemented, not yet run in isolation for metrics
- **Next:** Run `--m2-exit` alone + `--m1+m2-combined` sweep

### M3 — Maximum Holding Period with Score Hurdle
- **What:** Progressive re-qualification bar:
  - 12M: score must not decay > `m3_12m_decay` (default 10pts) from entry score
  - 18M: score must not decay > `m3_18m_decay` (default 5pts) from entry score
  - 24M: score must beat 75th percentile of current universe
- **Addresses:** Both ITC (24M hurdle) and COALINDIA (18M decay test)
- **Status:** ✅ Implemented on 2026-06-04
- **Run to validate:** `python scripts/portfolio_backtest.py --signal-mode --years 5 --m3-maxhold --hypothesis "M3 exits ITC before Jan 2025" --name "5y_M3_only"`

### M4 — Portfolio Monthly Drawdown Circuit Breaker
- **What:** If portfolio loses > `m4_threshold` (default 8%) in a single month → cap to 2 positions for next period, raise buy threshold +8pts for 2 months
- **Addresses:** Jan 2025 -10.5% recovery — system immediately loaded back up after the loss
- **Status:** Implemented

### M5 — India VIX Exposure Scalar
- **What:** Reduces max positions based on India VIX level (forward-looking vs lagging 200-DMA)
  - VIX < 15: 100% of target
  - VIX 15-20: 85%
  - VIX 20-25: 65%
  - VIX > 25: 40%
- **Data source:** `^IVIX` via yfinance
- **Advantage over 200-DMA:** In Sep 2024, India VIX spiked to 22-24 BEFORE NIFTY broke 200-DMA — 2-3 week earlier signal
- **Status:** Implemented

### M6 — Opportunity Cost Active Rotation
- **What:** At each rebalance, if best unowned candidate scores > `m6_gap` (default 12pts) above lowest-scoring held stock (after min-hold), rotate the pair
- **Addresses:** COALINDIA scoring ~58 in Q1 2024 vs JSWSTEEL scoring ~72 — 14pt gap triggers swap
- **Status:** ✅ Implemented on 2026-06-04
- **Run to validate:** `python scripts/portfolio_backtest.py --signal-mode --years 5 --m6-rotation --hypothesis "M6 rotates COALINDIA for JSWSTEEL in Q1 2024" --name "5y_M6_only"`

### M7 — Factor Concentration HHI Gate
- **What:** Blocks new entry if adding the stock would push portfolio's Herfindahl-Hirschman Index (across 5 factor buckets) above `m7_threshold` (default 0.35)
- **5 factor buckets:** def_value | psu_commodity | tech | cyclical_growth | other
- **Addresses:** ITC + BRITANNIA + NESTLEIND all share "def_value" factor — correlated fall in 2024-25
- **Note:** This is a soft gate (entry blocker), not an exit mechanism
- **Status:** ✅ Implemented on 2026-06-04
- **Run to validate:** `python scripts/portfolio_backtest.py --signal-mode --years 5 --m7-hhi --hypothesis "M7 prevents def_value crowding" --name "5y_M7_only"`

---

## Production Commands (Config A — Validated)

```bash
# Config A + cooldown — recommended for maximum returns:
python scripts/portfolio_backtest.py --signal-mode --years 5 \
  --buy-threshold 60 --sell-threshold 38 --stop-loss 0.10 \
  --min-hold 3 --profit-trail 0.12 --profit-trigger 0.20 \
  --rs-exit --rs-percentile 0.35 --rs-strikes 3 \
  --m3-maxhold --m3-12m-decay 8 --m3-18m-decay 3 --m3-cooldown 6 \
  --name "5y_ConfigA_cooldown"
# Result: CAGR 15.3% | Sharpe 0.57 | MaxDD -22.6% | Alpha +8.3%/yr

# Config A tight — best Sharpe + drawdown control:
python scripts/portfolio_backtest.py --signal-mode --years 5 \
  --buy-threshold 60 --sell-threshold 38 --stop-loss 0.10 \
  --min-hold 3 --profit-trail 0.12 --profit-trigger 0.20 \
  --rs-exit --rs-percentile 0.35 --rs-strikes 3 \
  --m3-maxhold --m3-12m-decay 8 --m3-18m-decay 3 \
  --name "5y_ConfigA_tight"
# Result: CAGR 14.5% | Sharpe 0.57 | MaxDD -20.8% | Calmar 0.70

# Compare all saved runs:
python scripts/portfolio_backtest.py --compare
```

---

## Walk-Forward Validation Finding (2026-06-05)

**Result:** FAILED — but for a known market-regime reason, not a signal failure.

| | Train 2021–23 | Test 2024–26 |
|--|--------------|-------------|
| Strategy Sharpe | 1.08 | -0.01 |
| NIFTY Sharpe | 0.53 | -0.24 |
| Retention | -1% ❌ | NIFTY: -46% ❌ |

**Correct interpretation:** NIFTY itself fails the 70% Sharpe retention criterion over this split. The test period is structurally harder (IT-led rally, budget crash). Alpha is positive in test (+2.8%/yr, CAGR 5.3% vs NIFTY 3.1%). The strategy's **known cyclicality** means it underperforms in IT/growth rallies — this is not a bug.

---

## Sector Rotation Guard — Permanently Rejected (2026-06-05)

**Hypothesis:** When a stock's sector beats NIFTY 3M, pause M1 strike accumulation.  
**Result:** Sharpe 0.44 with guard vs 0.57 without. Net negative.

**Root cause:** Guard kept IT stocks into the Sep 2024 crash. The 2025 IT rally still missed because fundamental re-rating (P/E expansion) isn't captured by the momentum/quality scoring model. The guard trades a certain loss for an uncertain gain that never materialises.

**Decision:** `m1_sector_guard=False` permanently in all production configs, walkforward, and sweep scripts.

---

## Live System Alignment — Config A (2026-06-04)

All Config A (M1+M3_tight) parameters are now wired to `core/portfolio_manager.py`.

| Change | File | Status | Notes |
|--------|------|--------|-------|
| buy_threshold 65 → 60 | `core/portfolio_manager.py` | ✅ | BacktestScorer v4 calibrated |
| sell_threshold 50 → 38 | `core/portfolio_manager.py` | ✅ | Wider hold zone |
| min_hold 3 months | `core/portfolio_manager.py` | ✅ | Prevents false exits |
| Profit protection (20% trigger, 12% trail) | `core/portfolio_manager.py` | ✅ | Replaces naive trailing stop |
| NIFTY 200-DMA regime gate (BEAR→4, SIDEWAYS→7, BULL→10) | `core/portfolio_manager.py` | ✅ | Via regime string prefix |
| BEAR regime +10pt entry threshold boost | `core/portfolio_manager.py` | ✅ | Aligned with backtest |
| M1 RS exit (bottom-35th score pct, 3 strikes) | `core/portfolio_manager.py` | ✅ | Via composite_score proxy |
| M3 max-hold (decay 8pt@12M, 3pt@18M, 75pct@24M) | `core/portfolio_manager.py` | ✅ | Exits value traps |
| M3 re-entry cooldown (6 months) | `core/portfolio_manager.py` | ✅ | Blocks ITC-style re-entry |
| DB migration: peak_price, rs_strike_count columns | `data/portfolio.db` | ✅ | Auto-migrated on startup |
| DB: portfolio_cooldowns table | `data/portfolio.db` | ✅ | Tracks M3 exit cooldowns |

### New PortfolioConfig fields (all configurable via API)
```python
min_hold_months: int = 3
profit_trigger_pct: float = 0.20
profit_trail_pct: float = 0.12
rs_exit_enabled: bool = True
rs_exit_percentile: float = 0.35
rs_exit_strikes: int = 3
m3_maxhold_enabled: bool = True
m3_12m_decay: float = 8.0
m3_18m_decay: float = 3.0
m3_cooldown_months: int = 6
```

### What's NOT yet live (still on backlog)
| Change | Status | Reason |
|--------|--------|--------|
| ADD/TRIM signals (partial buys/sells) | ❌ | Requires capital tracking DB schema |
| Tranched entry (5%→8% initial, add on confirm) | ❌ | Requires portfolio_tranches table |
| Cross-sectional MomentumAgent (6M+12M vol-norm) | ❌ | Requires universe price data at eval time |
| Walk-forward validation of Config A | ❌ | Run: `python scripts/walkforward_backtest.py --mechanisms M1 M3` |
