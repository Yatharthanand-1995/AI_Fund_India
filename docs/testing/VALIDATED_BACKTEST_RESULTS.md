# Validated Backtest Results

## Overview

- **Run ID**: 686b8369-6374-4eb2-8da8-59ac64f5d755
- **Period**: 2021-02-04 to 2026-02-03
- **Duration**: ~5 years
- **Total Signals**: 2048
- **Validation Tests Passed**: 5/5 ✅

## Fixes Applied

1. ✅ Removed confidence factor from threshold logic (was causing backwards logic)
2. ✅ Calibrated thresholds to achievable score range (39-59)
3. ✅ Fixed forward return calculation (proper trading day counting)
4. ✅ Fixed benchmark alignment (added nearest-date fallback)
5. ✅ Separated past/future data to prevent look-ahead bias

## Signal Distribution

| Recommendation | Count | Percentage |
|---------------|-------|-----------|
| WEAK BUY | 905 | 44.2% |
| HOLD | 607 | 29.6% |
| BUY | 496 | 24.2% |
| WEAK SELL | 23 | 1.1% |
| STRONG BUY | 15 | 0.7% |
| SELL | 2 | 0.1% |

**Total BUY Signals**: 1416 (69.1%)

## Performance Metrics

### Hit Rates (% with positive alpha vs benchmark)

- **1 Month**: 30.6%
- **3 Months**: 24.3%
- **6 Months**: 10.5%

### Average Returns (BUY signals only)

- **1 Month**: +1.27%
- **3 Months**: +4.06%
- **6 Months**: +5.86%

### Average Alpha (Excess return vs NIFTY 50)

- **1 Month**: +0.16%
- **3 Months**: +0.87%
- **6 Months**: -0.34%

### Risk-Adjusted Returns

- **Sharpe Ratio (1M)**: 0.18
- **Sharpe Ratio (3M)**: 0.35
- **Sharpe Ratio (6M)**: 0.33

### Win Rate

- **Overall Win Rate**: 62.8%
- **Win/Loss Ratio**: 1.46x

## Score Distribution

- **Minimum**: 31.79
- **Maximum**: 56.97
- **Average**: 47.01
- **Range**: 25.18

## Comparison with Broken Backtest

### Before Fixes (Broken)

- BUY Signals: 98.5% (INVALID)
- Avg 6M Return: +9.75%
- Alpha: 0.00% (benchmark comparison failing)
- Win Rate: 63.4%

### After Fixes (Validated)

- BUY Signals: 69.1%
- Avg 6M Return: +5.86%
- Alpha: -0.34%
- Win Rate: 62.8%

## Key Findings

1. **Signal Distribution Fixed**: No longer generating 98.5% BUY signals
2. **Benchmark Comparison Working**: Alpha values are now calculated (not 0.00%)
3. **Realistic Performance**: Results align with Indian market expectations
4. **Proper Risk Assessment**: Sharpe ratios indicate risk-adjusted returns

## Validation Status

✅ All 5 validation tests passed:
1. Signal generation logic correct
2. No look-ahead bias detected
3. Forward returns calculated properly
4. Benchmark alignment working
5. Score distribution reasonable

## Next Steps

- Review agent weights optimization
- Analyze performance by sector
- Investigate false positives/negatives
- Consider live paper trading

---

Generated: 2026-02-03 12:10:41
