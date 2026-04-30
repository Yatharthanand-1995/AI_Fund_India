# AI Hedge Fund System — India Edition Blueprint

> **Purpose**: A complete implementation guide for building an AI-powered stock analysis system for Indian equity markets (NSE/BSE), modelled on the US system architecture. Share this document with any team building a similar system.

---

## Overview

This blueprint describes how to build a **6-agent AI scoring system** for Indian equities, identical in architecture to the US system but adapted for NSE/BSE market structure, Indian regulatory filings (SEBI), and India-specific data signals (FII/DII flows, promoter holdings, GST macro).

**Target outcome (US system reference):** Exp 78 achieved +183.74%, Sharpe 1.18, Max DD -16.30% over a 5-year backtest. The India system should be calibrated and validated independently — do not assume the same absolute returns; use relative comparisons (strategy A vs B).

---

## Architecture Summary

The system has four layers:

```
Data Collection → 6-Agent Scoring → Composite Score → API + Frontend
                        ↑
              Regime-Adaptive Weights (optional)
```

**Stack:** Python 3.11+, FastAPI, React + TypeScript, TA-Lib, yfinance (with `.NS` suffix), Pydantic v2, Anthropic SDK.

---

## Key India Adaptations at a Glance

| Component | US System | India Adaptation |
|-----------|-----------|-----------------|
| Exchange suffix | (none) | `.NS` for NSE, `.BO` for BSE |
| Benchmark index | SPY | `^NSEI` (NIFTY 50) or `^BSESN` (SENSEX) |
| Volatility index | VIX (`^VIX`) | India VIX (`^INDIAVIX`) — verified working symbol |
| Universe | US Top 100 | NIFTY 100 or NIFTY 500 |
| Regulatory filings | SEC EDGAR | BSE/NSE corporate filing portals |
| Filing agent | EarningsQualityAgent via EDGAR | Same agent, NSE/BSE API adaptor |
| Institutional flow | OBV, MFI, CMF | **FII/DII net flows** + OBV, MFI |
| Settlement | T+2 → T+1 | T+1 (since Jan 2023) |
| Financial year | Jan–Dec | **Apr–Mar** (FY2026 = Apr 2025–Mar 2026) |
| Transaction cost | 10 bps/side | **25–30 bps/side** (STT + brokerage + GST) |
| Backtest start | Feb 2021 | **Jan 2020** (pre-COVID reference point) |

---

## Section 1 — Universe

### Recommended: NIFTY 100

The NIFTY 100 (top 100 NSE-listed companies by free-float market cap) is the Indian equivalent of the S&P 100. It provides:
- High liquidity (no execution slippage at retail/small-fund scale)
- Survivorship bias is manageable (NIFTY 100 constituents are relatively stable)
- Broad sector coverage

```python
# data/india_top_100_stocks.py
NIFTY_100_SYMBOLS = [
    # Large-cap IT
    "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTI.NS",
    # Banking (Private)
    "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS",
    # Banking (PSU)
    "SBIN.NS", "BANKBARODA.NS", "CANBK.NS", "PNB.NS",
    # FMCG
    "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
    # Pharma
    "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "AUROPHARMA.NS",
    # Auto
    "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS",
    # Energy / Oil & Gas
    "RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "NTPC.NS", "POWERGRID.NS",
    # Metals & Mining
    "TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "VEDL.NS", "COALINDIA.NS",
    # Conglomerates / Infra
    "ADANIENT.NS", "ADANIPORTS.NS", "ADANIGREEN.NS", "LT.NS", "ULTRACEMCO.NS",
    # Financials (non-bank)
    "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFC.NS", "MUTHOOTFIN.NS", "SBILIFE.NS",
    # Consumer Discretionary
    "ASIANPAINT.NS", "PIDILITIND.NS", "TITAN.NS", "HAVELLS.NS", "VOLTAS.NS",
    # Telecom
    "BHARTIARTL.NS", "IDEA.NS",
    # Healthcare
    "APOLLOHOSP.NS", "MAXHEALTH.NS",
    # Chemicals
    "PIIND.NS", "SRF.NS", "DEEPAKNTR.NS",
    # Others
    "TATACONSUM.NS", "GODREJCP.NS", "MARICO.NS", "COLPAL.NS",
    # Add more to reach 100 ...
]

SECTOR_MAPPING = {
    "TCS.NS": "IT", "INFY.NS": "IT", "WIPRO.NS": "IT",
    "HCLTECH.NS": "IT", "TECHM.NS": "IT",
    "HDFCBANK.NS": "Private Bank", "ICICIBANK.NS": "Private Bank",
    "KOTAKBANK.NS": "Private Bank", "AXISBANK.NS": "Private Bank",
    "SBIN.NS": "PSU Bank", "BANKBARODA.NS": "PSU Bank",
    "HINDUNILVR.NS": "FMCG", "ITC.NS": "FMCG", "NESTLEIND.NS": "FMCG",
    "SUNPHARMA.NS": "Pharma", "DRREDDY.NS": "Pharma", "CIPLA.NS": "Pharma",
    "MARUTI.NS": "Auto", "TATAMOTORS.NS": "Auto", "M&M.NS": "Auto",
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy", "BPCL.NS": "Energy",
    "TATASTEEL.NS": "Metal", "HINDALCO.NS": "Metal", "JSWSTEEL.NS": "Metal",
    "BAJFINANCE.NS": "NBFC", "BAJAJFINSV.NS": "NBFC",
    "LT.NS": "Infrastructure", "ADANIPORTS.NS": "Infrastructure",
    "BHARTIARTL.NS": "Telecom",
    "ASIANPAINT.NS": "Consumer", "TITAN.NS": "Consumer",
    # ... extend for full 100
}
```

### Yahoo Finance Symbol Format

NSE stocks use `.NS` suffix. BSE stocks use `.BO`. Always prefer `.NS` (more liquid, better data coverage).

```python
# yfinance works directly with .NS suffix
import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
hist = ticker.history(period="1y")
```

---

## Section 2 — Data Provider

### `data/enhanced_provider_india.py`

This is the equivalent of `data/enhanced_provider.py`. The logic is identical — fetch OHLCV data, run TA-Lib indicators, cache. The only changes:

1. Replace SPY benchmark with NIFTY 50 (`^NSEI`)
2. Append `.NS` to all symbols before yfinance calls
3. Add FII/DII data fetching (see Institutional Flow section)

```python
class EnhancedNSEProvider:
    BENCHMARK_SYMBOL = "^NSEI"   # NIFTY 50 Total Return equivalent
    INDIA_VIX = "^NSEINDVIX"

    def get_data(self, symbol: str) -> dict:
        # Ensure .NS suffix
        yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)
        # ... same indicator calculation as US system
```

### TA-Lib Indicators

No changes needed — TA-Lib is exchange-agnostic. All 40+ indicators (RSI, MACD, Bollinger, OBV, MFI, CMF, ADX, ATR, etc.) work identically on Indian OHLCV data.

### Data Quality Notes

- **yfinance coverage for Indian stocks**: Good for price history back to ~2005 for large-caps. Fundamental data (P/E, ROE etc. via `ticker.info`) is available but can lag by 1-2 quarters.
- **Historical fundamentals**: For point-in-time (PIT) backtesting, fundamental data from `ticker.info` reflects current values, not historical — same limitation as the US system. Apply the same PIT fixes (60-day lag filter for annual filings).
- **Dividends**: Indian companies often pay higher dividend yields (especially PSUs). Adjust total return calculations to include dividends.

---

## Section 3 — 6-Agent Architecture (India Adapted)

Weights below are starting suggestions. **Recalibrate via backtesting** before going live. The US system took 78 experiments to converge — expect a similar calibration journey.

### Proposed Starting Weights

```python
# config/agent_weights.py
STATIC_AGENT_WEIGHTS = {
    'fundamentals':       0.30,  # 30% — same role, Indian ratios
    'momentum':           0.25,  # 25% — unchanged, TA-Lib agnostic
    'quality':            0.15,  # 15% — unchanged
    'sentiment':          0.07,  # 07% — adjusted for Indian data availability
    'institutional_flow': 0.11,  # 11% — HIGHER: FII/DII is the dominant signal in India
    'earnings_quality':   0.12,  # 12% — SEBI filing analysis via LLM
}
# Must sum to 1.0
```

**Why FII/DII weight is higher (11% vs 8%)**: In Indian markets, Foreign Institutional Investor (FII) flows are the single most watched "smart money" signal. Large FII outflows reliably precede corrections; sustained FII buying precedes rallies. This signal is more actionable in India than pure price-volume (OBV) proxies.

---

### Agent 1: FundamentalsAgent (minimal changes)

**File:** `agents/fundamentals_agent.py`

The scoring logic (P/E, ROE, EV/EBITDA, revenue growth, debt ratios) transfers directly. Indian-specific adjustments:

| Metric | US Threshold | India Threshold | Reason |
|--------|-------------|-----------------|--------|
| P/E ratio | >30 = expensive | >40 = expensive for IT; >20 for PSU banks | Sector norms differ |
| Dividend yield | Not heavily weighted | Add +3–5 pts for yield >3% | PSUs trade on yield |
| Debt-to-equity | >2 = high | >1.5 = high for NBFC/financials | RBI leverage norms |
| ROE | >15% = good | >15% = good | Same threshold works |
| Revenue growth | YoY % | YoY % | Same logic |

**Financial year**: Indian companies report April–March. When computing YoY growth, align periods to FY not CY.

```python
def _get_financial_year(date: datetime) -> str:
    """Returns FY string like 'FY2026' for a given date."""
    if date.month >= 4:
        return f"FY{date.year + 1}"
    return f"FY{date.year}"
```

**ROIC adjustment (Exp 78 finding)**: The ROIC post-composite adjustment (+5/+3/+1/-3 pts for >25%/>15%/>8%/<0% ROIC) transfers directly. Indian capital-intensive sectors (metals, infra, energy) often have lower ROIC — ensure the financial-sector guard (`if sector in ('PSU Bank', 'Private Bank', 'NBFC'): skip`) excludes banking stocks from ROIC penalty.

---

### Agent 2: MomentumAgent (no changes needed)

**File:** `agents/momentum_agent.py`

RSI, MACD, moving averages, price momentum — entirely agnostic to market. The only change is that the benchmark comparison uses `^NSEI` instead of SPY.

**Momentum crash protection**: Indian markets experienced sharp momentum crashes in Mar 2020 (COVID), Oct 2021 (FII selloff), and Jan 2022 (rate-hike fear). The US system's "MAG 7" exemption concept applies here for NIFTY heavyweights:

```python
# agents/momentum_agent.py
NIFTY_HEAVYWEIGHTS = {'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'}
# Exempt from momentum veto — these always recover
```

**Negative return penalties (Exp 78 fix M-1)**: The symmetric penalty for negative momentum is critical — keep it.

---

### Agent 3: QualityAgent (minor changes)

**File:** `agents/quality_agent.py`

Business model quality scoring works the same. India-specific calibration:

- **Market-cap tiers**: Adjust for INR denomination. NIFTY 100 companies range from ~₹30,000 Cr to ₹20,00,000 Cr. Tier thresholds should be in INR Crores, not USD billions.
- **Moat scoring**: IT services firms (TCS, Infosys) have strong moats via client switching costs. PSU banks have implicit government backing (different moat type). Parameterise accordingly.
- The Exp 78 fix (Q-1: reducing market-cap tier points ~30%) is correct — apply it from the start. Avoid over-rewarding size.

---

### Agent 4: SentimentAgent (moderate changes)

**File:** `agents/sentiment_agent.py`

**Data sources for India:**

| Source | US Equivalent | India Source |
|--------|--------------|-------------|
| Analyst ratings | Yahoo Finance / Bloomberg | NSE/BSE via yfinance `ticker.recommendations` |
| Price targets | Bloomberg | Limited — yfinance `ticker.analyst_price_targets` where available |
| News sentiment | NewsAPI | Moneycontrol RSS, Economic Times API, Google News RSS |
| LLM news analysis | OpenAI/Anthropic/Gemini | Same — Gemini free tier works well |

**Analyst revision window**: Use the same 90-day recency-weighted revision window (the Exp 77 live upgrade). Indian brokerage reports are published quarterly around earnings season (Oct, Jan, Apr, Jul).

**Dispersion signal**: `(targetHigh - targetLow) / targetMean` — works identically.

**Without analyst data**: Many mid-caps in NIFTY 100 have sparse analyst coverage. When `ticker.recommendations` is empty, fall back to `score=50.0, confidence=0.2` (neutral with low confidence) rather than the 0.05 EQ fallback — sentiment simply has less information, not no information.

---

### Agent 5: InstitutionalFlowAgent — **Key India Adaptation**

**File:** `agents/institutional_flow_agent_india.py`

This is the most significant adaptation. In Indian markets, **FII/DII net flow data is publicly available** from NSE and is a far stronger signal than OBV proxies.

#### FII/DII Data

NSE publishes daily FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor) net buy/sell data on their website. This data is for the **entire market** (not per-stock), making it a **macro regime signal** rather than a stock-level signal.

**Use it as a regime filter, not a scoring signal:**

```python
class FIIDIIRegimeFilter:
    """
    Downloads daily FII/DII net flows from NSE.
    Returns a regime multiplier applied to momentum and IF scores.
    """

    def get_fii_regime(self, lookback_days: int = 20) -> dict:
        """
        Returns:
          {
            'fii_net_20d': float,    # Net FII flow last 20 days (Cr INR)
            'regime': 'buying' | 'selling' | 'neutral',
            'score_multiplier': float  # 0.85–1.15
          }
        """
        # Fetch from NSE API or a scraper/CSV
        # NSE publishes: https://www.nseindia.com/api/fiidiiTradeReact
        # Requires session headers (NSE blocks plain requests)
        ...
```

**Per-stock institutional ownership**: yfinance provides `ticker.institutional_holders` — use this as a quarterly snapshot to measure institutional ownership trend (increasing = positive signal).

#### Stock-Level IF Score (keep existing OBV/MFI/CMF logic)

The existing OBV, MFI, CMF, ADX indicators work on NSE data without modification. The Exp 78 fix (IF-1: MFI direction correction — oversold correctly scored lower) is critical — apply from day one.

**Remove VWAP** from the IF agent as per Exp 57 finding (Bernstein 2003: VWAP is an execution benchmark, not a predictive signal).

#### Weights within IF agent (India starting point)

```python
# 40% OBV + 35% MFI + 25% CMF (no VWAP)
# Same as Exp 57 configuration — validated improvement
```

#### Bulk/Block Deals (India-specific bonus signal)

NSE publishes daily bulk and block deal data. A large block deal at a premium is a strong institutional conviction signal. Optional: add +3 to +5 points to IF score when a block deal occurred in the last 5 trading days above 5-day VWAP.

```python
# NSE bulk deals API: https://www.nseindia.com/api/block-deal
# Block deal > 0.5% of total shares at premium > 1% → IF score +4
```

---

### Agent 6: EarningsQualityAgent — **Filing Adaptor Required**

**File:** `agents/earnings_quality_agent_india.py`

The US system reads SEC EDGAR (CIK lookup → 10-K/10-Q → MD&A extraction → Claude LLM analysis). For India, replace EDGAR with BSE/NSE filing portals.

#### Indian Filing Sources

| US | India Equivalent |
|----|-----------------|
| SEC EDGAR | BSE Corporate Filings (https://www.bseindia.com) |
| CIK lookup | BSE scrip code or NSE symbol |
| 10-K annual report | Annual Report PDF (filed with BSE/NSE) |
| 10-Q quarterly | Quarterly Results PDF (filed within 45 days of quarter-end) |
| MD&A section | "Management Discussion and Analysis" section in AR |

**BSE Filing API:**
```python
# BSE provides an undocumented JSON API for filings
# https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
# Params: strCat=Annual+Reports&scripcode=<BSE_CODE>
# Returns list of filing URLs

def get_latest_annual_report_url(bse_scrip_code: str) -> str:
    url = f"https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    params = {"strCat": "Annual Reports", "scripcode": bse_scrip_code}
    # Parse response to extract PDF URL
    ...
```

**NSE Filing API:**
```python
# NSE annual reports
# https://www.nseindia.com/api/annual-reports?index=equities&symbol=<SYMBOL>
```

**Accruals calculation (Sloan anomaly)**: Same formula — no India-specific changes needed:
```
Accruals ratio = (Net Income - Operating Cash Flow) / Avg Total Assets
High accruals (>5%) = earnings quality concern
```

**LLM prompt for Indian MD&A**: Same structure as US prompt, add India-specific guidance:

```python
INDIA_EARNINGS_QUALITY_PROMPT = """
Analyze this Indian company's Management Discussion and Analysis section.
Focus on:
1. Revenue quality: Is growth organic or driven by one-time items?
2. Working capital: Are receivables growing faster than revenue? (Common in Indian IT services)
3. Promoter commentary: Any hedging language around guidance?
4. Regulatory risks: GST changes, RBI policy impact (for financials), PLI scheme dependency
5. Related party transactions: Flag if material and unexplained
6. Debt profile: Has debt increased YoY? Is it for capex or working capital?

Return a JSON with: accruals_risk (low/medium/high), management_credibility (0-10),
key_risks (list), red_flags (list).
"""
```

**Fallback**: Same as US — `score=50.0, confidence=0.05` when `ANTHROPIC_API_KEY` is absent.

---

## Section 4 — Regime Detection

### `ml/regime_detector_india.py`

Replace SPY-based regime detection with NIFTY 50 (`^NSEI`) and India VIX (`^NSEINDVIX`).

#### Indian Market Regimes

| Regime | Trigger | Weight Shift |
|--------|---------|-------------|
| Bull | NIFTY 50 > 200-day MA + FII net buying | More momentum |
| Bear | NIFTY 50 < 200-day MA + FII net selling | More fundamentals + quality |
| High Volatility | India VIX > 25 | More quality, less momentum |
| FII Exodus | 10-day FII net sell > ₹15,000 Cr | Raise quality bar, cut IF weight |
| Budget Rally | Feb 1 ± 5 days (Union Budget) | Suppress momentum signals (noise event) |
| Earnings Season | Apr/Jul/Oct/Jan (results months) | Raise EQ weight temporarily |
| Election Season | ~6 weeks pre-general election | Raise sentiment weight, flag high uncertainty |

**All 9 regime maps must sum to 1.0 and include all 6 agents** — same validation rule as US system.

```python
INDIA_REGIME_WEIGHTS = {
    'bull_market': {
        'fundamentals': 0.27, 'momentum': 0.30, 'quality': 0.14,
        'sentiment': 0.07, 'institutional_flow': 0.11, 'earnings_quality': 0.11
    },
    'bear_market': {
        'fundamentals': 0.36, 'momentum': 0.18, 'quality': 0.19,
        'sentiment': 0.06, 'institutional_flow': 0.10, 'earnings_quality': 0.11
    },
    # ... 7 more regimes, all summing to 1.0
}
```

---

## Section 5 — Backtesting Engine

### Key Configuration Differences

```python
@dataclass
class IndiaBacktestConfig:
    start_date: str = "2020-01-01"   # Pre-COVID baseline
    end_date: str = "2025-12-31"
    initial_capital: float = 1_00_00_000.0  # ₹1 Crore
    benchmark_symbol: str = "^NSEI"

    # India-specific transaction costs
    # Brokerage (flat ₹20/trade Zerodha) + STT 0.1% sell + exchange 0.00345%
    # + GST 18% on (brokerage + exchange) + stamp duty 0.015% buy side
    # Effective: ~25-30 bps per side (vs US 10 bps)
    transaction_cost_bps: float = 27.0

    # Same risk-free rate — use 10-year G-Sec yield (~7%)
    risk_free_rate: float = 0.07

    # Score drop exit — same mechanism, validated in US system
    use_score_drop_exit: bool = True
    score_drop_exit_threshold: float = 52.0
    score_drop_check_days: int = 10  # ~bi-weekly (same as Exp 33c)

    # Entry gate — same 60-point threshold
    min_composite_score_for_entry: float = 60.0

    # Position sizing — conviction-based (same as Exp 53E)
    use_conviction_sizing: bool = True
    max_position_size: float = 0.12  # 12% max single position

    # Stop loss — 20% MED base (validated Exp 78)
    position_stop_loss: float = 0.20
```

### India-Specific Backtest Adjustments

1. **Circuit breakers**: Indian stocks have daily ±5%/10%/20% price limits. In extreme cases (like Yes Bank crisis, Adani selloff), the circuit breaker fires repeatedly. Handle this by capping single-day returns at ±20% in historical simulation.

2. **Delisted stocks**: Several NIFTY 100 constituents were delisted or had governance crises (Yes Bank, DHFL, IL&FS). Build a delisting database and handle gracefully (exit at last available price).

3. **Rights issues and bonus shares**: Indian companies frequently issue bonus shares (e.g., 1:1) and rights issues. yfinance adjusts for splits but not all corporate actions. Validate adjusted close prices.

4. **F&O expiry effect**: Indian markets show a predictable pattern around NSE F&O expiry (last Thursday of each month) — short-term volatility spike. Avoid rebalancing on expiry day.

5. **Budget day**: Union Budget (Feb 1) causes extreme volatility. Do not rebalance on Budget day.

6. **Holidays**: India has more market holidays than US (~15/year). Use `pandas_market_calendars` with the `'NSE'` calendar.

```python
import pandas_market_calendars as mcal
nse = mcal.get_calendar('NSE')
valid_days = nse.valid_days(start_date='2020-01-01', end_date='2025-12-31')
```

### Backtest Reference Period

| Period | Key Events | Expected System Behavior |
|--------|-----------|--------------------------|
| Jan–Mar 2020 | COVID crash (-38% NIFTY) | Should stay out or exit via score-drop |
| Apr–Dec 2020 | V-shaped recovery (+82% from March low) | Should re-enter high-quality names |
| 2021 | Bull run (+24% NIFTY) | Strong performance year |
| Jan 2022 | Rate-hike fear correction (-15%) | FII exodus signal should fire |
| 2023 | Recovery + IT weakness | Quality gate keeps out weak IT mid-caps |
| 2024 | Election rally + Budget rally | High-beta performance |

---

## Section 6 — India-Specific Signals (Optional Experiments)

These are signals with no US equivalent. Test each as a separate experiment:

### Signal: Promoter Holding Trend

Indian law requires promoters to disclose shareholding quarterly. A sustained increase in promoter holding (>1% per quarter) is a strong insider-conviction signal.

```python
def get_promoter_holding_trend(symbol: str) -> dict:
    """
    BSE shareholding pattern API:
    https://api.bseindia.com/BseIndiaAPI/api/ShareHoldingPatterns/w?scripcode=<CODE>
    Returns quarterly promoter holding %.
    Score: +3 if promoter % increased last 2 quarters, -3 if decreased
    """
    ...
```

### Signal: FII vs DII Divergence

When FIIs are selling but DIIs are buying aggressively, Indian mutual funds (DIIs) are providing a support floor. This historically marks near-term lows.

```python
def get_fii_dii_divergence_score(lookback_days: int = 10) -> float:
    """
    FII net < -5000 Cr AND DII net > +3000 Cr → score +5 (buying opportunity)
    FII net > +5000 Cr AND DII net < -1000 Cr → score -3 (late rally caution)
    """
    ...
```

### Signal: Piotroski F-Score (same as US Exp 56)

The Piotroski F-Score works identically on Indian financial statements. Apply the same stop-tier logic from Exp 63: F≥7 → looser stops (30%), F≤2 → tighter stops (10%).

### Signal: GST Collection Growth (Macro Filter)

India's monthly GST collection data is a leading indicator of economic activity. Published by MoF on the 1st of each month.

```python
# GST > ₹1.8L Cr = strong economy → allow normal entry threshold
# GST < ₹1.4L Cr = weak economy → raise entry threshold to 63
# Source: https://www.pib.gov.in (public press releases)
```

### Signal: PLI Scheme Beneficiaries

The Production Linked Incentive (PLI) scheme covers 14 sectors. Companies receiving PLI benefits have government-backed revenue visibility. Optional: add +2 pts to fundamentals score for confirmed PLI recipients.

---

## Section 7 — Data APIs and Libraries

### Required Python Packages

```text
# requirements.txt additions for India system
yfinance>=0.2.36
pandas>=2.0
numpy>=1.24
ta-lib-binary  # or TA-Lib from source
anthropic>=0.84.0   # For EarningsQualityAgent
pydantic>=2.0
fastapi>=0.110
pandas-market-calendars>=4.3  # For NSE holiday calendar
requests>=2.31
beautifulsoup4>=4.12  # For BSE/NSE filing scraping
```

### Optional: Broker APIs for Live Trading

| Broker | API | Free? | Notes |
|--------|-----|-------|-------|
| Zerodha | `kiteconnect` (pip) | Free for customers | Most popular, well-documented |
| Angel One | `smartapi-python` (pip) | Free for customers | Good data APIs |
| Upstox | `upstox-python-sdk` (pip) | Free for customers | REST + WebSocket |
| Fyers | `fyers-apiv3` (pip) | Free for customers | Good historical data |

**For backtesting only**: yfinance is sufficient. Broker APIs are needed only for live order execution.

### NSE Data APIs (Unofficial but Stable)

```python
# NSE requires browser-like headers — use a session
import requests

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com",
}

def get_nse_data(endpoint: str, params: dict = None) -> dict:
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=NSE_HEADERS)  # Get cookies
    response = session.get(
        f"https://www.nseindia.com/api/{endpoint}",
        headers=NSE_HEADERS, params=params
    )
    return response.json()

# Examples:
# get_nse_data("fiidiiTradeReact")              # FII/DII daily data
# get_nse_data("quote-equity?symbol=RELIANCE")  # Stock quote
# get_nse_data("block-deal")                    # Block deals
```

---

## Section 8 — API Layer

### Changes from US `api/main.py`

1. **Currency**: All portfolio values in INR (₹), not USD
2. **Recommendation thresholds**: Same logic, same 60/70/52 thresholds — recalibrate only after backtesting
3. **Symbols**: Strip `.NS`/`.BO` suffix for display; add back for yfinance calls
4. **Market hours**: 9:15 AM – 3:30 PM IST (UTC+5:30)
5. **Health check**: Same 4+/6 healthy agents required

```python
# api/main.py additions
from datetime import timezone
import pytz

IST = pytz.timezone('Asia/Kolkata')

def is_market_open() -> bool:
    now_ist = datetime.now(IST)
    if now_ist.weekday() >= 5:  # Saturday, Sunday
        return False
    market_open = now_ist.replace(hour=9, minute=15, second=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0)
    return market_open <= now_ist <= market_close
```

---

## Section 9 — Frontend Adaptations

The React + TypeScript frontend requires only cosmetic changes:

| US | India |
|----|-------|
| `$` currency symbol | `₹` |
| "S&P 500" references | "NIFTY 50" / "NIFTY 100" |
| "SEC filing" | "BSE/NSE filing" |
| "Analyst consensus" | "Broker consensus" (Kotak, ICICI Securities, Motilal etc.) |
| Market hours display | IST timezone |

No architectural changes to the frontend are needed.

---

## Section 10 — Backtesting Validation Protocol

Follow the same validation protocol as the US system:

### Step 1: Establish Baseline

Run the vanilla system (no regime-adaptive weights, default 60-point threshold, 20% stops) on the 2020–2025 period. Record:
- Total return
- Sharpe ratio
- Max drawdown
- Annual breakdown

This is your **India Baseline** — equivalent to US Exp Baseline (+62.3%).

### Step 2: A/B Experiment Discipline

- Change ONE variable per experiment
- Use the baseline as the reference for every new experiment
- If a change hurts Sharpe, reject it — even if return improves
- If a change causes more score-drop exits (the 52-68 band instability problem), reject it

### Step 3: Walk-Forward Validation

Before declaring any configuration as "champion", run a walk-forward out-of-sample test:
- Train window: 2020–2023
- Test windows: quarterly OOS periods in 2024–2025
- A valid champion should show OOS Sharpe within 0.2 of in-sample

### Known India-Specific Anti-Patterns (Do Not Retry Without Evidence)

1. **FII flow as a stock-level signal**: FII data is market-aggregate, not per-stock. Use as regime filter only.
2. **Sector rotation based on Budget**: Sector beneficiaries are priced in quickly. By execution time, the edge is gone.
3. **PLI scheme bonus**: Government policies change. A point-in-time PIT issue — hard to backtest honestly.
4. **Mid-cap extension**: Extending universe beyond NIFTY 100 adds liquidity risk. Validate separately before including mid-caps.
5. **Promoter holding as entry signal**: Works better as a conviction boost (+2 to existing score) than as an entry gate.

---

## Section 11 — Known Biases (Same as US System)

| Bias | Estimated Impact | Mitigation |
|------|-----------------|-----------|
| Survivorship bias | +5–15% | Use dynamic universe with delisting database |
| Look-ahead bias (fundamentals) | +3–8% | Apply 60-day lag on annual filings |
| Survivorship (Adani/Yes Bank) | High | Manually add delisted constituents back |
| FII flow look-ahead (2020 COVID) | Moderate | FII data published same day — use T-1 lag |

**Rule**: All backtest comparisons are **relative** (India strategy A vs India strategy B). Never cite absolute returns as real-world expectations.

---

## Section 12 — Quick-Start Checklist

### Environment Setup

```bash
# 1. Clone the US system repo as the starting template
git clone <repo>

# 2. Install dependencies
pip install -r requirements.txt
pip install pandas-market-calendars kiteconnect smartapi-python

# 3. Set environment variables
export ANTHROPIC_API_KEY=<key>      # Required for EarningsQualityAgent
export GEMINI_API_KEY=<key>          # For sentiment LLM (free tier)
export LLM_PROVIDER=gemini           # Recommended default
export ENABLE_ADAPTIVE_WEIGHTS=false # Off until backtested

# 4. Run weight validator
python tests/test_weight_validator.py  # Must show all weights sum to 1.0

# 5. Run baseline backtest (2020-2025)
python scripts/backtesting/run_india_baseline.py

# 6. Verify baseline is stable before any experiments
```

### Files to Create / Modify

| File | Action | Priority |
|------|--------|----------|
| `data/india_top_100_stocks.py` | Create — NIFTY 100 universe + sector map | P0 |
| `data/enhanced_provider_india.py` | Modify — swap SPY→^NSEI, add .NS suffix | P0 |
| `config/agent_weights.py` | Modify — use India starting weights | P0 |
| `core/backtesting_engine.py` | Modify — `transaction_cost_bps=27`, `risk_free_rate=0.07`, NSE calendar | P0 |
| `agents/institutional_flow_agent_india.py` | Create — add FII/DII regime filter | P1 |
| `agents/earnings_quality_agent_india.py` | Create — BSE/NSE filing adaptor | P1 |
| `ml/regime_detector_india.py` | Create — NIFTY/VIX-based regime maps | P1 |
| `api/main.py` | Modify — IST timezone, INR currency | P2 |
| `frontend/src/` | Modify — ₹ symbol, NIFTY references | P2 |

---

## Section 13 — Reference Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │          INDIA AI HEDGE FUND             │
                    └─────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┼──────────────────────────┐
              │                         │                          │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌──────────▼─────────┐
    │   Data Collection  │   │   6-Agent Scoring   │   │    Regime Detect   │
    │                   │   │                     │   │                    │
    │ yfinance (.NS)    │   │ F: 30% Fundamentals │   │ NIFTY 50 (^NSEI)   │
    │ NSE unofficial API│   │ M: 25% Momentum     │   │ India VIX          │
    │ BSE filing API    │   │ Q: 15% Quality      │   │ FII/DII 20d net    │
    │ FII/DII NSE API   │   │ S: 07% Sentiment    │   │                    │
    │ TA-Lib (40+ ind.) │   │ IF:11% Inst. Flow   │   │ 9 Regime Maps      │
    │                   │   │ EQ:12% Earnings     │   │ (each sums to 1.0) │
    └───────────────────┘   └─────────────────────┘   └────────────────────┘
                                        │
                            ┌───────────▼───────────┐
                            │   Composite Score 0-100│
                            │   + Recommendation     │
                            │   + Narrative (LLM)    │
                            └───────────────────────┘
                                        │
              ┌─────────────────────────┼──────────────────────┐
              │                         │                       │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌───────▼────────┐
    │   FastAPI (8080)   │   │  React Frontend     │   │ Backtesting    │
    │   /analyze         │   │  (TypeScript)       │   │ Engine v2.5    │
    │   /portfolio       │   │  INR / NIFTY refs   │   │ NSE Calendar   │
    │   /market/regime   │   │                     │   │ 27bps cost     │
    └───────────────────┘   └─────────────────────┘   └────────────────┘
```

---

## Appendix A — Sector Map (India)

```python
INDIA_SECTOR_RISK_MULTIPLIERS = {
    'IT':           0.90,   # High quality, cyclical but recovers
    'Private Bank': 1.00,   # Market beta ~1
    'PSU Bank':     1.20,   # Higher risk, regulatory/NPL exposure
    'NBFC':         1.15,   # IL&FS/DHFL legacy risk
    'FMCG':         0.80,   # Defensive, low beta
    'Pharma':       0.95,   # Moderate — US FDA risk
    'Auto':         1.10,   # Cyclical, EV transition risk
    'Energy':       1.10,   # Oil price sensitive (PSU subsidy risk)
    'Metal':        1.25,   # Highly cyclical, China demand dependent
    'Infrastructure': 1.15, # Execution/debt risk
    'Telecom':      1.20,   # Capital intensive, tariff risk
    'Consumer':     0.90,   # Discretionary — urban demand proxy
}
```

---

## Appendix B — Transaction Cost Breakdown (India)

| Cost Component | Rate | Side |
|---------------|------|------|
| Brokerage (Zerodha flat) | ₹20/trade or 0.03% (whichever lower) | Both |
| STT (Securities Transaction Tax) | 0.1% | Sell only |
| NSE exchange charges | 0.00335% | Both |
| GST on (brokerage + exchange) | 18% | Both |
| SEBI charges | 0.0001% | Both |
| Stamp duty | 0.015% | Buy only |
| **Effective total (approx)** | **~27–30 bps/side** | — |

For backtesting, use `transaction_cost_bps = 27.0` (conservative estimate).

---

## Appendix C — Key India Financial APIs

| Data | Source | Type |
|------|--------|------|
| Stock prices (historical) | `yfinance` with `.NS` suffix | Python library |
| Fundamental data | `yfinance` `ticker.info` | Python library |
| FII/DII daily flows | NSE API `/api/fiidiiTradeReact` | HTTP (needs session) |
| Block/bulk deals | NSE API `/api/block-deal` | HTTP (needs session) |
| Annual reports | BSE API `AnnSubCategoryGetData` | HTTP |
| Quarterly results | NSE API `/api/annual-reports` | HTTP |
| Shareholding pattern | BSE API `ShareHoldingPatterns` | HTTP |
| NSE holiday calendar | `pandas_market_calendars` (`NSE`) | Python library |
| India VIX | `yfinance` symbol `^NSEINDVIX` | Python library |
| NIFTY indices | `yfinance` `^NSEI`, `^NSMIDCP` | Python library |

---

*Document version: 1.0 | Based on US AI Hedge Fund System — Exp 78 champion | April 2026*
*Architecture reference: `CLAUDE.md` + `docs/SYSTEM_MAP.md` in the US system repository*
