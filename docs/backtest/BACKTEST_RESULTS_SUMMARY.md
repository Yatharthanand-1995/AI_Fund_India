# 5-Year NIFTY 50 Backtest Results

## Executive Summary

**Date**: 2026-02-03
**Run ID**: `569a79b9-b5df-48f0-b03c-0090c901d108`
**Duration**: 1.3 minutes
**Status**: ✅ Complete

The comprehensive 5-year backtest on NIFTY 50 stocks has been completed successfully, generating **2,887 trading signals** across **48 stocks** from February 2021 to February 2026.

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Signals | 2,887 |
| BUY Signals | 0 (0%) |
| SELL Signals | 2,447 (84.8%) |
| WEAK SELL Signals | 440 (15.2%) |
| Execution Time | 1.3 minutes |
| Date Range | 2021-02-04 to 2026-02-03 |
| Stocks Analyzed | 48 |
| Backtest Dates | 61 (monthly) |

## Performance Metrics

### Hit Rates (% Positive Alpha vs NIFTY 50)
- **1 Month**: 0.0%
- **3 Months**: 0.0%
- **6 Months**: 0.0%

*Note: Hit rate is 0% because all signals were SELL, and we measure BUY signal performance*

### Average Alpha by Signal Type
| Signal Type | Count | Avg 3M Alpha | Hit Rate |
|-------------|-------|--------------|----------|
| WEAK SELL | 440 | +1.37% | 47.3% |
| SELL | 2,447 | +0.39% | 46.2% |

### Risk Metrics
- **Sharpe Ratio (3M)**: 0.00 (no BUY signals)
- **Max Drawdown**: 0.00%
- **Win Rate**: 0.0%
- **Win/Loss Ratio**: 0.00x

## Agent Performance Analysis

### Correlation with 3-Month Alpha

| Agent | Correlation | Predictive Power | Current Weight | Optimal Weight |
|-------|-------------|------------------|----------------|----------------|
| Momentum | +0.150 | Weak | 27% | **46.2%** ⬆ |
| Fundamentals | nan | Weak | 36% | **40.4%** ⬆ |
| Sentiment | nan | Weak | 9% | **13.4%** ⬆ |
| Quality | +0.044 | Weak | 18% | **0.0%** ⬇ |
| Institutional Flow | -0.016 | Weak | 10% | **0.0%** ⬇ |

### Key Observations

1. **Momentum Agent** shows the strongest (though still weak) positive correlation
2. **Fundamentals & Sentiment** show NaN correlations (no score variation)
3. **Institutional Flow** shows slight negative correlation
4. **Quality** shows minimal positive correlation

## Critical Findings

### 🚨 Issue 1: Only SELL Signals Generated

**Problem**: All 2,887 signals were SELL or WEAK SELL. Zero BUY signals.

**Possible Causes**:
1. **Recommendation thresholds too strict**: Current thresholds may be:
   - STRONG BUY: ≥80
   - BUY: ≥68
   - WEAK BUY: ≥58
   - HOLD: 45-57
   - SELL: <45

2. **Agent scores too low**: Agents consistently scoring below 58

3. **Period characteristics**: 2021-2026 may have been challenging for Indian markets

**Impact**: Cannot measure BUY signal performance, limiting backtest usefulness

**Recommended Action**:
- Analyze score distribution
- Adjust thresholds to generate balanced signals
- Investigate why agents score consistently low

### 🚨 Issue 2: Fundamentals & Sentiment No Variation

**Problem**: Both agents returned NaN correlations, indicating they gave identical scores across all stocks/dates.

**Likely Cause**:
- Missing fundamental data in backtest mode
- Sentiment agent returning default 50.0 scores
- These agents may not work with historical price-only data

**Impact**: Two agents (45% combined weight) contributing no differentiation

**Recommended Action**:
- Check if fundamentals data is available for historical dates
- Consider lower weights for these agents during backtests
- Log sample scores to verify the issue

### 🚨 Issue 3: Weak Predictive Power

**Problem**: Correlations range from -0.016 to +0.150, all very weak

**Impact**: System has minimal ability to predict forward returns

**Possible Causes**:
- Agents not properly calibrated
- Missing fundamental data reduces signal quality
- Market conditions don't match agent assumptions
- Look-ahead bias eliminated, revealing true performance

**Recommended Action**:
- Deep dive into individual agent performance
- Test with more recent data where fundamentals may be available
- Consider feature engineering improvements

## Optimal Weight Recommendations

Based on linear regression optimization:

```python
OPTIMAL_WEIGHTS = {
    'fundamentals': 0.404,      # ⬆ +4.4% from 0.36
    'momentum': 0.462,          # ⬆ +19.2% from 0.27
    'quality': 0.000,           # ⬇ -18.0% from 0.18
    'sentiment': 0.134,         # ⬆ +4.4% from 0.09
    'institutional_flow': 0.000 # ⬇ -10.0% from 0.10
}
```

**Expected Sharpe Improvement**: -1.286 (negative - indicates current weights may be better)

**Note**: This recommendation is based on weak correlations and should be validated with additional analysis.

## Detailed Recommendations

### Immediate Actions

1. **Investigate Score Distribution**
   ```python
   # Analyze why all scores are below BUY threshold
   - Check agent score distributions
   - Identify if thresholds need adjustment
   - Verify agent calculations are working correctly
   ```

2. **Fix Fundamentals & Sentiment Agents**
   ```python
   # These agents show no variation - likely returning defaults
   - Verify fundamental data availability in cached_data
   - Check sentiment agent with historical data
   - Consider excluding these from backtest if data unavailable
   ```

3. **Adjust Recommendation Thresholds**
   ```python
   # Consider more lenient thresholds for balanced signals:
   RECOMMENDED_THRESHOLDS = {
       'STRONG BUY': 70,  # Lower from 80
       'BUY': 58,         # Lower from 68
       'WEAK BUY': 50,    # Lower from 58
       'HOLD': 40-50,
       'SELL': <40
   }
   ```

### Medium-Term Improvements

4. **Enhance Agent Capabilities**
   - Add historical fundamental data fetching
   - Improve momentum calculations
   - Refine quality metrics
   - Better institutional flow detection

5. **Feature Engineering**
   - Add more technical indicators
   - Incorporate market regime detection
   - Add sector rotation signals
   - Volume-weighted metrics

6. **Validation Strategy**
   - Run backtest on different time periods
   - Test on individual sectors
   - Walk-forward validation
   - Out-of-sample testing

### Long-Term Optimizations

7. **Machine Learning Integration**
   - Use backtest data to train ML models
   - Automated weight optimization
   - Dynamic threshold adjustment
   - Pattern recognition for regime changes

8. **Risk Management**
   - Portfolio construction rules
   - Position sizing algorithms
   - Stop-loss strategies
   - Correlation-based diversification

9. **Live Trading Preparation**
   - Paper trading system
   - Real-time signal generation
   - Performance monitoring dashboard
   - Alert mechanisms

## Technical Implementation Notes

### What Worked Well ✅

1. **Date Alignment**: Fixed trading day mismatch with nearest-neighbor matching
2. **Point-in-Time Data**: Successfully eliminated look-ahead bias
3. **Parallel Processing**: Achieved 1.3-minute runtime for 2,887 signals
4. **Database Storage**: All results properly saved and retrievable
5. **Analysis Pipeline**: Complete end-to-end workflow functional

### Bugs Fixed During Implementation 🐛

1. **Look-ahead bias** (line 264): Fixed by passing cached_data
2. **JSON serialization**: Fixed numpy type conversion
3. **Benchmark symbol**: Fixed Yahoo Finance index handling
4. **Date matching**: Implemented nearest trading day logic
5. **Analysis serialization**: Fixed dataclass to dict conversion

## Data Quality Assessment

### Available Data
- ✅ Historical price data (OHLCV)
- ✅ Benchmark data (NIFTY 50 index)
- ✅ Technical indicators (computed from price)
- ❌ Historical fundamental data (limited)
- ❌ Historical sentiment data (not available)

### Data Coverage
- **Date Range**: 2021-02-04 to 2026-02-03 (5 years)
- **Frequency**: Daily price data
- **Completeness**: ~90% of requested dates (some gaps)
- **Source**: Yahoo Finance (NSEpy incompatible with Python 3.13)

## Next Steps

### Option 1: Fix and Re-run (Recommended)
1. Adjust recommendation thresholds
2. Fix Fundamentals/Sentiment agents
3. Re-run backtest with corrections
4. Compare results

### Option 2: Analyze Current Results
1. Build frontend visualization (Tasks 6-7)
2. Deep dive into score distributions
3. Identify specific failure modes
4. Document learnings

### Option 3: Optimize and Iterate
1. Implement optimal weights
2. Test different threshold configurations
3. Run sensitivity analysis
4. A/B test different approaches

### Option 4: Production Deployment
1. Build real-time signal generation
2. Create monitoring dashboard
3. Implement alerting system
4. Begin paper trading

## Files Generated

| File | Purpose | Location |
|------|---------|----------|
| Database | Backtest results | `data/backtest_history.db` |
| Report | Text summary | `backtest_results/backtest_20260203_112526.txt` |
| Logs | Detailed execution log | `backtest_run_fixed.log` |
| This Document | Analysis summary | `BACKTEST_RESULTS_SUMMARY.md` |

## API Access

### View All Runs
```bash
curl http://localhost:8000/backtest/runs
```

### Get Run Details
```bash
curl http://localhost:8000/backtest/results/569a79b9-b5df-48f0-b03c-0090c901d108
```

### Get Analysis
```bash
curl http://localhost:8000/backtest/analysis/569a79b9-b5df-48f0-b03c-0090c901d108
```

### Delete Run
```bash
curl -X DELETE http://localhost:8000/backtest/results/569a79b9-b5df-48f0-b03c-0090c901d108
```

## Conclusion

The 5-year NIFTY 50 backtest infrastructure is **fully functional** and successfully processed 2,887 signals in just 1.3 minutes. However, the results reveal critical issues with:

1. **Signal generation** (only SELL signals)
2. **Agent variation** (Fundamentals & Sentiment)
3. **Predictive power** (weak correlations)

These findings provide valuable insights for system improvement. The next priority should be investigating why all signals are SELL and fixing the Fundamentals/Sentiment agents to provide proper variation.

---

**Status**: ✅ Backtest Infrastructure Complete | ⚠️ System Calibration Needed
**Next Milestone**: Fix signal generation and re-run backtest
**Last Updated**: 2026-02-03
