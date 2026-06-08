# System Redesign Plan — Live Alignment + Capital Deployment Logic
**Date:** 2026-06-01 | Status: Approved for implementation

---

## The Problem Statement

The system has two modes that don't talk to each other:

```
BACKTEST MODE                    LIVE MODE
──────────────────────           ──────────────────────────
Custom scoring formula           5-agent StockScorer
  60% momentum                    36% Fundamentals
  40% quality proxy               27% Momentum (RSI/MACD)
                                  18% Quality
Binary all-in, all-out           Binary BUY/SELL
Equal-weight / score-weight      Equal-weight only
0% or 100% deployed              No capital tracking
```

**What we want:**

```
UNIFIED SYSTEM
──────────────────────────────────────────────────────
Same 5-agent scoring formula in both backtest and live
Tranched buying — start small, build on conviction
Monthly capital deployment (SIP-style)
Partial exits when thesis weakens
NIFTY regime filter gates all entries
```

---

## Part 1: Scoring Alignment — The Bridge Formula

### Why we can't run the full 5-agent scorer in backtest

Running `StockScorer.score_stock()` for 50 stocks × 60 months = 3,000 calls, each taking ~2-5 seconds in live mode (API calls, parallel agents). That's **4-8 hours for one backtest run**.

### What we can do: `BacktestScorer` — same weights, historical data

Create a `BacktestScorer` that uses the **exact same agent weights** as the live system but computes each agent score from the historical price + fundamentals data we already have.

| Agent | Live Source | Backtest Proxy | Historical Availability |
|-------|------------|----------------|------------------------|
| Fundamentals (36%) | yfinance fundamentals + earnings | P/E rank in universe + earnings growth YoY | quarterly financials via yfinance ✓ |
| Momentum (27%) | RSI, MACD, 6M/12M RS | 6M+12M vol-normalized cross-sectional (NSE method) | price history ✓ |
| Quality (18%) | Piotroski, debt, margins | ROE + ROCE + D/E (annual refresh) | quarterly balance sheet ✓ |
| Sentiment (9%) | News, analyst ratings | **50.0 (neutral)** — no historical data | ✗ (use constant) |
| Institutional Flow (10%) | Delivery %, OI, FII proxy | FII 20-day net flow regime (60/50/40) | NSE daily FII data ✓ |

### The BacktestScorer composite

```python
# backtest/backtest_scorer.py (new file)

class BacktestScorer:
    """
    Mirrors StockScorer.STATIC_WEIGHTS but computes each agent from historical data.
    Produces scores that are directly comparable to live system output.
    
    Weights (same as StockScorer.STATIC_WEIGHTS):
      fundamentals: 0.36
      momentum:     0.27
      quality:      0.18
      sentiment:    0.09  → always 50 (neutral — no historical news)
      inst_flow:    0.10  → FII regime proxy
    """
    
    WEIGHTS = {'fundamentals': 0.36, 'momentum': 0.27, 'quality': 0.18,
               'sentiment': 0.09, 'institutional_flow': 0.10}
    
    def score(self, sym, prices, bench_prices, as_of_date,
              quality_cache, fii_regime) -> Dict[str, float]:
        
        # Fundamentals score (0-100)
        # = P/E percentile rank within universe (lower P/E = higher score) × 40
        #   + earnings growth score (YoY EPS growth) × 40
        #   + ROE trend score (improving ROE) × 20
        f_score = self._fundamentals_score(sym, as_of_date, quality_cache)
        
        # Momentum score (0-100) — NSE Momentum 30 methodology
        # = vol-normalized 6M return (skip last 1M) cross-sectional Z-score
        # + vol-normalized 12M return (skip last 1M) cross-sectional Z-score
        # normalized to 0-100
        m_score = self._momentum_score_cross_sectional(sym, prices, as_of_date)
        
        # Quality score (0-100) — from annual quality cache
        # = ROE score (0-40) + D/E score (0-35) + ROCE proxy (0-25)
        q_score = quality_cache.get(sym, 25.0)
        
        # Sentiment: 50 (neutral placeholder)
        s_score = 50.0
        
        # Institutional flow: FII regime
        # bull_regime → 65, neutral → 50, bear_regime → 35
        i_score = {'bull': 65.0, 'neutral': 50.0, 'bear': 35.0}.get(fii_regime, 50.0)
        
        composite = (self.WEIGHTS['fundamentals'] * f_score
                   + self.WEIGHTS['momentum'] * m_score
                   + self.WEIGHTS['quality'] * q_score
                   + self.WEIGHTS['sentiment'] * s_score
                   + self.WEIGHTS['institutional_flow'] * i_score)
        
        return {
            'composite': composite,
            'fundamentals': f_score,
            'momentum': m_score,
            'quality': q_score,
            'sentiment': s_score,
            'inst_flow': i_score,
        }
```

### Fix MomentumAgent for live system

The live `MomentumAgent._score_returns()` currently uses:
- 1M return (contributes up to 5 pts out of 100)
- 3M return (contributes up to 15 pts)
- 6M return (contributes up to 10 pts)

**Add cross-sectional momentum method to MomentumAgent:**

```python
# agents/momentum_agent.py — add to MomentumAgent class

def cross_sectional_score(
    self,
    symbol: str,
    price_data: pd.DataFrame,
    universe_prices: Dict[str, pd.DataFrame],  # all NIFTY50 stocks for ranking
) -> float:
    """
    NSE Momentum 30 style cross-sectional score.
    - Skip last 1 month (avoid reversal contamination)
    - Use 6M and 12M returns normalized by realized volatility
    - Z-score within universe
    - Return normalized to 0-100
    
    This is the component that generates the factor premium.
    """
    def get_normalized_return(prices, months, skip_months=1):
        # Return from (months+skip) ago to skip months ago
        skip_days = skip_months * 21
        lookback_days = months * 21
        n = len(prices)
        if n < lookback_days + skip_days + 1:
            return None
        p_end   = prices.iloc[-(skip_days)]           # 1M ago
        p_start = prices.iloc[-(lookback_days + skip_days)]  # 7M ago for 6M
        ret = (p_end - p_start) / p_start if p_start > 0 else None
        if ret is None:
            return None
        # Normalize by annualized vol of that period
        period_returns = prices.iloc[-(lookback_days + skip_days):-(skip_days)].pct_change().dropna()
        vol = period_returns.std() * np.sqrt(252)
        return ret / vol if vol > 0 else None
    
    # Compute normalized 6M and 12M for all universe stocks
    scores_6m = {}
    scores_12m = {}
    for sym, sym_prices in universe_prices.items():
        if isinstance(sym_prices, pd.DataFrame):
            closes = sym_prices['Close']
        else:
            closes = sym_prices
        s6 = get_normalized_return(closes, 6)
        s12 = get_normalized_return(closes, 12)
        if s6 is not None: scores_6m[sym] = s6
        if s12 is not None: scores_12m[sym] = s12
    
    if not scores_6m or not scores_12m:
        return 50.0  # fallback to neutral
    
    # Z-score within universe
    def z_score(sym, score_dict):
        vals = list(score_dict.values())
        mean, std = np.mean(vals), np.std(vals)
        if std == 0: return 0.0
        return (score_dict.get(sym, mean) - mean) / std
    
    z6  = z_score(symbol, scores_6m)
    z12 = z_score(symbol, scores_12m)
    combined_z = 0.5 * z6 + 0.5 * z12
    
    # Convert z-score to 0-100 (z=+2 → 98, z=-2 → 2)
    percentile = scipy.stats.norm.cdf(combined_z) * 100
    return float(np.clip(percentile, 0, 100))
```

---

## Part 2: Capital Deployment Logic — The New Investment Model

### Philosophy shift

**Old model:** At each monthly review, compute top-N stocks, deploy equal capital to all of them.  
→ Treats every stock the same regardless of conviction level.

**New model:** Build positions incrementally like a professional investor.  
→ Start small, add on confirmation, protect with trailing stops, harvest on weakness.

### The 3-Tier Position System

```
                    TIER 1          TIER 2          TIER 3
                    ──────────      ──────────      ──────────
Score Level:        ≥ 75            65-75           55-65
Label:              STRONG BUY      BUY             WATCH
Initial Capital:    8% of portfolio 5% of portfolio 0% (no capital)
Can Add to?:        Yes             Yes             No
Max Size:           15% portfolio   12% portfolio   N/A

HOLD ZONE:          score 40-65 for existing positions (no new money, don't exit yet)
EXIT ZONE:          score < 40 → immediate full exit
PARTIAL EXIT:       score dropped 12+ pts from entry_score → trim 50%
STOP LOSS:          price down 10% from peak (trailing stop)
```

### Monthly Review Cycle (the engine)

Every month (last trading day), the system runs this sequence:

```
STEP 0: REGIME CHECK
────────────────────
• Compute NIFTY 200-DMA status
  - BULL (price > 200-DMA AND > 50-DMA): max_positions=10, max_equity=90%, cash_floor=10%
  - SIDEWAYS (price > 200-DMA, < 50-DMA): max_positions=7, max_equity=75%, cash_floor=25%
  - BEAR (price < 200-DMA): max_positions=4, max_equity=50%, cash_floor=50%

• Compute event risk scalar
  - Budget week (Jan 26 – Feb 5): reduce max_equity by 30%
  - RBI MPC ±3 days: reduce max_equity by 15%
  - F&O expiry day: suppress new entries only

STEP 1: EXITS (always first — free up capital before deploying)
────────────────────────────────────────────────────────────────
For each open position:
  a. If price < trailing_stop → EXIT 100% (SELL_STOP)
  b. If composite_score < sell_threshold (40) → EXIT 100% (SELL_SCORE)
  c. If composite_score dropped > 12pts from entry_score → TRIM 50% (SELL_PARTIAL)
  d. If stock no longer in point-in-time NIFTY50 → EXIT (DELISTED_REMOVED)

STEP 2: ADDS (existing positions, new monthly capital first)
─────────────────────────────────────────────────────────────
For each held position still qualifying (score ≥ 40):
  If score improved ≥ 3pts from last review
  AND current score ≥ buy_threshold
  AND position size < max_size_for_tier
  AND price ≥ entry_price (not adding to a loser)
  AND monthly_budget remaining > 0:
    → ADD monthly_add_per_position to this stock
       (prioritised by highest score: STRONG BUY stocks get more)

STEP 3: NEW ENTRIES
────────────────────
Sort all universe stocks by score descending.
For each non-held stock with score ≥ buy_threshold:
  If n_positions < max_positions[regime]
  AND sector cap allows
  AND available capital ≥ BASE_POSITION_SIZE
  AND NOT in F&O expiry window:
    → ENTER with BASE_POSITION_SIZE (5% for BUY, 8% for STRONG BUY)
    → Set trailing_stop at entry_price × (1 - stop_loss_pct)
    → Record entry_score for future partial-exit decisions

STEP 4: SIZING ADJUSTMENT
──────────────────────────
Apply volatility-adjusted sizing to all held positions:
  target_weight_i = (score_i / vol_i) / sum(score_j / vol_j for all j)
  Rebalance if actual weight deviates > 3% from target
  (small rebalancing bands prevent excessive churn)

STEP 5: CASH MANAGEMENT
─────────────────────────
  cash_pct = 1 - sum(position_weights)
  cash_pct must be ≥ cash_floor[regime]
  Monthly_cash_yield = cash × CASH_MONTHLY_RATE (6.5% p.a.)
```

### Capital Tracking — What Changes in the DB

The current `portfolio_holdings` table has:
```sql
symbol, entry_price, entry_score, entry_date, sector, trailing_stop_price
```

**New columns needed:**
```sql
position_size_pct      REAL DEFAULT 5.0,    -- current % of portfolio
initial_size_pct       REAL DEFAULT 5.0,    -- first tranche size
peak_score             REAL,                 -- highest score seen since entry
peak_price             REAL,                 -- for trailing stop calculation
last_add_date          TEXT,                 -- date of last add-to-position
n_tranches             INTEGER DEFAULT 1,    -- how many times we've added
tier                   TEXT DEFAULT 'BUY',   -- STRONG_BUY or BUY
```

**New table: `portfolio_tranches`** (tracks each buy separately for P&L)
```sql
CREATE TABLE portfolio_tranches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    tranche_date  TEXT NOT NULL,
    tranche_price REAL NOT NULL,
    tranche_score REAL NOT NULL,
    size_pct      REAL NOT NULL,   -- % of portfolio at time of purchase
    tranche_type  TEXT NOT NULL,   -- INITIAL | ADD | MONTHLY_SIP
    status        TEXT DEFAULT 'open'  -- open | closed
);
```

**Portfolio-level tracking:**
```sql
CREATE TABLE portfolio_state (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    total_capital REAL DEFAULT 100000.0,  -- INR, starting capital
    cash_balance  REAL DEFAULT 100000.0,  -- current cash
    monthly_sip   REAL DEFAULT 10000.0,   -- monthly add-in amount
    updated_at    TEXT
);
```

---

## Part 3: The New `run_tranched_simulation()` Function

Replace `run_signal_simulation()` in the backtest with this:

```python
def run_tranched_simulation(
    prices: Dict[str, pd.Series],
    bench: pd.Series,
    quality_cache: Dict,
    
    # Thresholds (from live system calibration)
    strong_buy_threshold: float = 75.0,
    buy_threshold: float = 65.0,
    hold_threshold: float = 40.0,    # below this = exit
    partial_exit_drop: float = 12.0, # pts below entry_score = trim 50%
    stop_loss: float = 0.10,
    
    # Capital deployment
    initial_capital: float = 100_000.0,  # INR
    monthly_sip: float = 10_000.0,       # add this much each month
    strong_buy_size_pct: float = 0.08,   # 8% of portfolio
    buy_size_pct: float = 0.05,          # 5% of portfolio
    max_position_pct: float = 0.15,      # max 15% in any one stock
    monthly_add_per_position: float = 0.025,  # max 2.5% add per review
    
    # Constraints
    max_positions_bull: int = 10,
    max_positions_sideways: int = 7,
    max_positions_bear: int = 4,
    sector_cap: float = 0.30,
    
    # Toggles
    use_backtest_scorer: bool = True,    # use live-aligned formula
    use_regime_filter: bool = True,      # NIFTY 200-DMA gate
    use_vol_sizing: bool = True,         # volatility-adjusted weights
    use_event_calendar: bool = True,     # budget day reduction
    
    transaction_cost: float = 0.0027,
    inr_prices: Optional[pd.Series] = None,
    rbi_history: Optional[List[Dict]] = None,
    
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Tranched position simulation.
    
    Tracks capital in INR (not just index-100).
    Allows partial exits and incremental adds.
    Uses BacktestScorer (live-aligned formula) when use_backtest_scorer=True.
    Applies NIFTY 200-DMA regime filter when use_regime_filter=True.
    """
```

### Position state object

```python
@dataclass
class Position:
    symbol: str
    tranches: List[Dict]         # [{date, price, score, size_pct, type}]
    total_capital: float         # actual INR invested
    entry_date: pd.Timestamp
    entry_score: float           # score at first tranche
    peak_score: float            # highest score ever seen
    peak_price: float            # for trailing stop
    trailing_stop: float
    tier: str                    # STRONG_BUY or BUY
    
    @property
    def avg_entry_price(self) -> float:
        total_cost = sum(t['price'] * t['capital'] for t in self.tranches)
        total_cap  = sum(t['capital'] for t in self.tranches)
        return total_cost / total_cap if total_cap > 0 else 0

    @property
    def position_size_pct(self) -> float:
        return self.total_capital / self.portfolio_value  # injected at runtime
```

---

## Part 4: Live `PortfolioManager` Changes

### Changes to `portfolio_manager.py`

**1. Add monthly SIP execution:**
```python
def execute_monthly_review(self, stock_scores: List[Dict], regime: str,
                            monthly_budget: float = 10000.0) -> EvaluationResult:
    """
    Full monthly review: exits → adds → new entries.
    Deploys monthly_budget: first to existing positions, then new entries.
    """
```

**2. Add partial exit signal (`SELL_PARTIAL`):**
```python
# In evaluate() — Step 1:
elif current_score < (h['entry_score'] - partial_exit_drop):
    signal = 'SELL_PARTIAL'
    reason = f"Score decay: entry {h['entry_score']:.0f} → now {current_score:.0f} (-{decay:.0f}pts). Trimming 50%."
    # Close 50% of the position (new close_partial_holding() method)
```

**3. Add ADD signal (conviction-building):**
```python
# After exits, for existing positions:
elif (current_score >= buy_threshold 
      and current_score > h['entry_score'] + score_improve_pts
      and current_price >= h['avg_entry_price']
      and h['position_size_pct'] < max_size_pct
      and monthly_budget_remaining > 0):
    signal = 'ADD'
    reason = f"Score improved {score_improve:.0f}pts, price confirmed. Adding position."
```

**4. Add regime gate:**
```python
# Before any BUY:
nifty_regime = self._get_nifty_regime()
if nifty_regime == 'BEAR' and n_positions >= max_positions_bear:
    signal = 'WATCH'
    reason = f"Bear regime: capped at {max_positions_bear} positions (NIFTY < 200-DMA)"
```

**5. Add `position_size_pct` to `Holding`:**
Track actual capital allocation per position, not just binary held/not-held.

### New `Holding` dataclass
```python
@dataclass
class Holding:
    id: int
    symbol: str
    entry_price: float
    entry_score: float
    entry_date: str
    sector: str
    current_price: Optional[float] = None
    current_score: Optional[float] = None
    return_pct: Optional[float] = None
    signal: str = 'HOLD'
    # NEW FIELDS:
    position_size_pct: float = 5.0        # % of total portfolio
    avg_entry_price: Optional[float] = None  # weighted avg across tranches
    peak_score: float = 0.0
    peak_price: Optional[float] = None
    n_tranches: int = 1
    tier: str = 'BUY'                     # STRONG_BUY | BUY
```

### New `SignalItem` types
```python
# Current signals: BUY | HOLD | SELL_SCORE | SELL_STOP | WATCH
# New signals:     BUY | ADD | HOLD | TRIM | SELL_SCORE | SELL_STOP | WATCH
#
# BUY      = new position, first tranche
# ADD      = adding to existing position (score improved, price confirmed)
# HOLD     = no action — thesis intact, no new money
# TRIM     = reduce position 50% (score decaying but not at exit level)
# SELL_*   = full exit (stop loss or score exit)
# WATCH    = qualified but can't enter (capacity, sector, regime, event)
```

---

## Part 5: What Changes in Which File

### New files

| File | Purpose |
|------|---------|
| `backtest/backtest_scorer.py` | Live-aligned scoring for backtest — same weights as StockScorer |
| `backtest/tranched_simulation.py` | New `run_tranched_simulation()` — capital-tracking, tranched entry |
| `core/calendar_risk_manager.py` | Budget day, RBI MPC, F&O expiry risk scalars |
| `core/regime_filter.py` | NIFTY 200-DMA regime detection for live system |

### Modified files

| File | Change | Why |
|------|--------|-----|
| `agents/momentum_agent.py` | Add `cross_sectional_score()` method using 6M+12M vol-normalized | Fixes wrong timescale — biggest alpha driver |
| `core/portfolio_manager.py` | Add ADD/TRIM signals, monthly SIP execution, regime gate, position sizing | Implements tranched buy logic for live |
| `core/portfolio_manager.py` | New DB columns: position_size_pct, peak_score, n_tranches, tier | Tracks conviction level per position |
| `scripts/portfolio_backtest.py` | Wire `BacktestScorer` as default scorer | Live-backtest alignment |
| `data/nifty50_historical.py` | SHREECEM fix ✓ already done | Data bug |

---

## Part 6: Parameter Calibration from Backtest

Once `BacktestScorer` is implemented and `run_tranched_simulation()` is running, calibrate these parameters:

| Parameter | Test Range | Metric to Optimize |
|-----------|-----------|-------------------|
| `strong_buy_threshold` | 70, 72, 75 | Alpha in NIFTY up months |
| `buy_threshold` | 60, 62, 65 | Total return |
| `hold_threshold` | 35, 40, 45 | Max drawdown |
| `partial_exit_drop` | 10, 12, 15 | Sharpe ratio |
| `stop_loss` | 8%, 10%, 12% | Calmar ratio |
| `strong_buy_size_pct` | 6%, 8%, 10% | Win rate |
| `monthly_sip` | varies | CAGR per unit of capital |

Run as grid or walk-forward: train on 2021-2023, validate on 2024-2026.

---

## Part 7: Target Outcomes

### Backtest targets (after all Phase 1+2 changes)

| Metric | Current | Phase 1 target | Phase 2 target |
|--------|---------|----------------|----------------|
| Total Return 5Y | +19.6% | +35-40% | +50-60% |
| CAGR | 3.7% | 6-8% | 9-12% |
| Sharpe | -0.22 | +0.10-0.20 | +0.30-0.45 |
| Max Drawdown | -15.2% | -12% | -10% |
| Monthly Win Rate | 51.7% | 58-62% | 63-68% |
| Feb 2026 single month | -13.1% | < -8% | < -6% |

### Live system targets

| Metric | Current | Target |
|--------|---------|--------|
| Signal thresholds | buy=65, sell=50 | buy=65, sell=40 (wider hold zone) |
| Position sizing | equal weight | score × 1/vol |
| Monthly deployment | one-time all-in | SIP + add-to-winners |
| Bear market behaviour | stays invested | reduces to 4 positions |
| Budget day | no protection | 30% equity reduction |

---

## Implementation Order

```
Week 1 — Foundation
  [x] Fix SHREECEM in historical data
  [ ] Implement NIFTY 200-DMA regime filter in backtest (quickest alpha win)
  [ ] Replace 1M momentum with 6M/12M cross-sectional in backtest scoring
  [ ] Run new baseline 5Y backtest with these two changes

Week 2 — Live Alignment
  [ ] Create BacktestScorer with live weights
  [ ] Add cross_sectional_score() to MomentumAgent (live)
  [ ] Add regime gate to PortfolioManager (live)
  [ ] Add TRIM signal and partial exit to PortfolioManager

Week 3 — Tranched Simulation
  [ ] Implement run_tranched_simulation() in backtest
  [ ] DB schema migration (position_size_pct, tranches table)
  [ ] Wire monthly SIP into PortfolioManager.execute_monthly_review()
  [ ] Add ADD signal to PortfolioManager

Week 4 — Calibration & Validation
  [ ] Parameter sweep on corrected 5Y (27 combinations)
  [ ] Walk-forward validation (train 2021-23, test 2024-26)
  [ ] Update live portfolio config based on validated parameters
  [ ] Document final thresholds in MEMORY.md
```
