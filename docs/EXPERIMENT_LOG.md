# Experiment Log — Indian Stock Fund Backtest
Auto-appended by scripts/portfolio_backtest.py after every run.
v4 baseline: CAGR 12.9% | Sharpe 0.42 | MaxDD -27.2% | Alpha +5.5%/yr

---

## 2026-06-04 13:23 — 5y_M3_isolated
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M3  
**CAGR:** 13.6% (+0.7% vs v4 baseline)  
**Sharpe:** 0.46 (+0.04)  
**MaxDD:** -27.8% (-0.6%)  
**Alpha/yr:** 6.5% (+1.0%)  
**WinRate:** 61.7%  
**Hypothesis:** M3 exits ITC before Jan 2025  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 13:27 — 5y_M1+M3+M6+M7
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3+M6+M7  
**CAGR:** 6.5% (-6.4% vs v4 baseline)  
**Sharpe:** -3699.68 (-3700.10)  
**MaxDD:** 0.0% (+27.2%)  
**Alpha/yr:** 6.5% (+1.0%)  
**WinRate:** 50.0%  
**Hypothesis:** M1+M3+M6+M7: target MaxDD < -20%  
**Verdict:** ❌ WORSE

---

## 2026-06-04 13:32 — 5y_M1+M3+M6+M7_v2
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3+M6+M7  
**CAGR:** 11.1% (-1.8% vs v4 baseline)  
**Sharpe:** 0.32 (-0.10)  
**MaxDD:** -24.1% (+3.1%)  
**Alpha/yr:** 4.5% (-1.0%)  
**WinRate:** 61.7%  
**Hypothesis:** M1+M3+M6+M7: target MaxDD < -20% (M7 bug fixed)  
**Verdict:** ❌ WORSE

---

## 2026-06-04 14:19 — 5y_M1+M3
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.0% (+2.1% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.7% (+4.5%)  
**Alpha/yr:** 8.0% (+2.5%)  
**WinRate:** 60.0%  
**Hypothesis:** M1+M3: does M3 prevent ITC re-entry after rank exit?  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 14:23 — 5y_M1+M2
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M2  
**CAGR:** 13.2% (+0.3% vs v4 baseline)  
**Sharpe:** 0.45 (+0.03)  
**MaxDD:** -23.1% (+4.1%)  
**Alpha/yr:** 6.2% (+0.7%)  
**WinRate:** 60.0%  
**Hypothesis:** M1+M2: M2 blocks ITC re-entry after 12M underperformance vs NIFTY  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 14:27 — 5y_M1+M6_gap18
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M6  
**CAGR:** 14.9% (+2.0% vs v4 baseline)  
**Sharpe:** 0.54 (+0.12)  
**MaxDD:** -23.8% (+3.4%)  
**Alpha/yr:** 8.0% (+2.5%)  
**WinRate:** 61.7%  
**Hypothesis:** M1+M6(gap18): less churn, still rotates COALINDIA in Q1 2024?  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 14:36 — 5y_M1+M3_tight
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 14.5% (+1.6% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -20.8% (+6.4%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** M1p35s3+M3(tighter): tighter M3 decay allowances 8/3 vs 10/5  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 14:36 — 5y_M1p40s2+M3
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 12.6% (-0.3% vs v4 baseline)  
**Sharpe:** 0.46 (+0.04)  
**MaxDD:** -16.8% (+10.4%)  
**Alpha/yr:** 7.2% (+1.7%)  
**WinRate:** 60.0%  
**Hypothesis:** M1(p40/s2)+M3: aggressive RS exit + age hurdle, can MaxDD break -20%?  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 14:36 — 5y_M1p35s2+M3
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 11.1% (-1.8% vs v4 baseline)  
**Sharpe:** 0.38 (-0.04)  
**MaxDD:** -15.0% (+12.2%)  
**Alpha/yr:** 6.2% (+0.7%)  
**WinRate:** 58.3%  
**Hypothesis:** M1(p35/s2)+M3: faster RS exit (2 strikes vs 3), same M3  
**Verdict:** ❌ WORSE

---

## 2026-06-04 21:48 — 5y_ConfigA_cooldown6
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.3% (+2.4% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Config A + M3 cooldown(6M): does blocking ITC re-entry fix Jan 2025?  
**Verdict:** ✅ IMPROVED

---

## 2026-06-04 21:53 — 5y_ConfigA_sectorguard
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 12.9% (+0.0% vs v4 baseline)  
**Sharpe:** 0.44 (+0.02)  
**MaxDD:** -22.7% (+4.5%)  
**Alpha/yr:** 6.2% (+0.7%)  
**WinRate:** 56.7%  
**Hypothesis:** Config A + sector guard only (no cooldown): isolate sector guard effect  
**Verdict:** ⚠️  MIXED

---

## 2026-06-04 21:53 — 5y_ConfigA_full
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 13.9% (+1.0% vs v4 baseline)  
**Sharpe:** 0.49 (+0.07)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 7.1% (+1.6%)  
**WinRate:** 55.0%  
**Hypothesis:** Config A + cooldown + sector guard: does IT sector guard fix 2025 miss?  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 00:28 — 5y_ConfigA_analysis
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.3% (+2.4% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** —  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 00:32 — 5y_ConfigA_analysis
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.3% (+2.4% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** —  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 00:55 — 5y_ConfigA_v2_allsignals
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.3% (+2.4% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Adding correlation guard + FCF yield + promoter pledge to BacktestScorer  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 01:02 — 5y_ConfigA_v2_FCF_CorrGuard
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 13.2% (+0.3% vs v4 baseline)  
**Sharpe:** 0.45 (+0.03)  
**MaxDD:** -27.2% (+0.0%)  
**Alpha/yr:** 6.0% (+0.5%)  
**WinRate:** 61.7%  
**Hypothesis:** FCF yield in BacktestScorer + correlation guard on entry  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 01:06 — 5y_ConfigA_v2_FCFonly
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 13.2% (+0.3% vs v4 baseline)  
**Sharpe:** 0.45 (+0.03)  
**MaxDD:** -27.2% (+0.0%)  
**Alpha/yr:** 6.0% (+0.5%)  
**WinRate:** 61.7%  
**Hypothesis:** FCF only, no corr guard — isolating FCF signal impact  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 01:12 — 5y_ConfigA_v2_FCFsectorguard
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 13.4% (+0.5% vs v4 baseline)  
**Sharpe:** 0.45 (+0.03)  
**MaxDD:** -27.2% (+0.0%)  
**Alpha/yr:** 6.2% (+0.7%)  
**WinRate:** 60.0%  
**Hypothesis:** FCF with Energy/Financials excluded + corr guard  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 01:16 — 5y_ConfigA_v2_final
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.3% (+2.4% vs v4 baseline)  
**Sharpe:** 0.57 (+0.15)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Correlation guard added (neutral), FCF reverted from scorer (lookahead bias)  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:19 — 5y_ConfigA_tightcorr_p60_1peer
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 16.2% (+3.3% vs v4 baseline)  
**Sharpe:** 0.62 (+0.20)  
**MaxDD:** -25.0% (+2.2%)  
**Alpha/yr:** 9.1% (+3.6%)  
**WinRate:** 63.3%  
**Hypothesis:** Tighter corr guard: block if any 1 held stock correlates >0.60 — targets Jan-2025 4-defensive cluster  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:25 — sweep_M1+M3_b58_s35_sl8
**Params:** buy=58.0 sell=35.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 15.2% (+2.3% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -25.8% (+1.4%)  
**Alpha/yr:** 7.9% (+2.4%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 1/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:25 — sweep_M1+M3_b58_s35_sl10
**Params:** buy=58.0 sell=35.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.9% (+3.0% vs v4 baseline)  
**Sharpe:** 0.60 (+0.18)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.6% (+3.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 2/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:25 — sweep_M1+M3_b58_s35_sl12
**Params:** buy=58.0 sell=35.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.1% (+3.2% vs v4 baseline)  
**Sharpe:** 0.61 (+0.19)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.7% (+3.2%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 3/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:25 — sweep_M1+M3_b58_s38_sl8
**Params:** buy=58.0 sell=38.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 15.2% (+2.3% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -25.8% (+1.4%)  
**Alpha/yr:** 7.9% (+2.4%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 4/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:25 — sweep_M1+M3_b58_s38_sl10
**Params:** buy=58.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.9% (+3.0% vs v4 baseline)  
**Sharpe:** 0.60 (+0.18)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.6% (+3.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 5/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b58_s38_sl12
**Params:** buy=58.0 sell=38.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.1% (+3.2% vs v4 baseline)  
**Sharpe:** 0.61 (+0.19)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.7% (+3.2%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 6/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b58_s40_sl8
**Params:** buy=58.0 sell=40.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 15.2% (+2.3% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -25.8% (+1.4%)  
**Alpha/yr:** 7.9% (+2.4%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 7/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b58_s40_sl10
**Params:** buy=58.0 sell=40.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.9% (+3.0% vs v4 baseline)  
**Sharpe:** 0.60 (+0.18)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.6% (+3.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 8/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b58_s40_sl12
**Params:** buy=58.0 sell=40.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.1% (+3.2% vs v4 baseline)  
**Sharpe:** 0.61 (+0.19)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 8.7% (+3.2%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 9/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s35_sl8
**Params:** buy=60.0 sell=35.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 14.5% (+1.6% vs v4 baseline)  
**Sharpe:** 0.52 (+0.10)  
**MaxDD:** -24.0% (+3.2%)  
**Alpha/yr:** 7.6% (+2.1%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 10/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s35_sl10
**Params:** buy=60.0 sell=35.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Grid sweep combo 11/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s35_sl12
**Params:** buy=60.0 sell=35.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 12/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s38_sl8
**Params:** buy=60.0 sell=38.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 14.5% (+1.6% vs v4 baseline)  
**Sharpe:** 0.52 (+0.10)  
**MaxDD:** -24.0% (+3.2%)  
**Alpha/yr:** 7.6% (+2.1%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 13/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s38_sl10
**Params:** buy=60.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Grid sweep combo 14/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s38_sl12
**Params:** buy=60.0 sell=38.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 15/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s40_sl8
**Params:** buy=60.0 sell=40.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 14.5% (+1.6% vs v4 baseline)  
**Sharpe:** 0.52 (+0.10)  
**MaxDD:** -24.0% (+3.2%)  
**Alpha/yr:** 7.6% (+2.1%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 16/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s40_sl10
**Params:** buy=60.0 sell=40.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 58.3%  
**Hypothesis:** Grid sweep combo 17/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b60_s40_sl12
**Params:** buy=60.0 sell=40.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 15.1% (+2.2% vs v4 baseline)  
**Sharpe:** 0.56 (+0.14)  
**MaxDD:** -22.6% (+4.6%)  
**Alpha/yr:** 8.3% (+2.8%)  
**WinRate:** 60.0%  
**Hypothesis:** Grid sweep combo 18/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s35_sl8
**Params:** buy=62.0 sell=35.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 16.0% (+3.1% vs v4 baseline)  
**Sharpe:** 0.62 (+0.20)  
**MaxDD:** -24.1% (+3.1%)  
**Alpha/yr:** 9.2% (+3.7%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 19/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s35_sl10
**Params:** buy=62.0 sell=35.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 20/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s35_sl12
**Params:** buy=62.0 sell=35.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 21/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s38_sl8
**Params:** buy=62.0 sell=38.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 16.0% (+3.1% vs v4 baseline)  
**Sharpe:** 0.62 (+0.20)  
**MaxDD:** -24.1% (+3.1%)  
**Alpha/yr:** 9.2% (+3.7%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 22/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s38_sl10
**Params:** buy=62.0 sell=38.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 23/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s38_sl12
**Params:** buy=62.0 sell=38.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 24/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s40_sl8
**Params:** buy=62.0 sell=40.0 sl=0.08 years=5 mechanisms=M1+M3  
**CAGR:** 16.0% (+3.1% vs v4 baseline)  
**Sharpe:** 0.62 (+0.20)  
**MaxDD:** -24.1% (+3.1%)  
**Alpha/yr:** 9.2% (+3.7%)  
**WinRate:** 61.7%  
**Hypothesis:** Grid sweep combo 25/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s40_sl10
**Params:** buy=62.0 sell=40.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 26/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:26 — sweep_M1+M3_b62_s40_sl12
**Params:** buy=62.0 sell=40.0 sl=0.12 years=5 mechanisms=M1+M3  
**CAGR:** 16.3% (+3.4% vs v4 baseline)  
**Sharpe:** 0.64 (+0.22)  
**MaxDD:** -21.1% (+6.1%)  
**Alpha/yr:** 9.6% (+4.1%)  
**WinRate:** 63.3%  
**Hypothesis:** Grid sweep combo 27/27  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:31 — 5y_ConfigB_b62s35_tightcorr
**Params:** buy=62.0 sell=35.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 17.6% (+4.7% vs v4 baseline)  
**Sharpe:** 0.70 (+0.28)  
**MaxDD:** -24.2% (+3.0%)  
**Alpha/yr:** 10.5% (+5.0%)  
**WinRate:** 68.3%  
**Hypothesis:** Config B: sweep-optimal b62/s35/sl10 + tight corr guard p60/1peer — testing signal stacking  
**Verdict:** ✅ IMPROVED

---

## 2026-06-06 22:44 — 5y_ConfigB_earnings_surprise
**Params:** buy=62.0 sell=35.0 sl=0.1 years=5 mechanisms=M1+M3  
**CAGR:** 19.4% (+6.5% vs v4 baseline)  
**Sharpe:** 0.82 (+0.40)  
**MaxDD:** -18.0% (+9.2%)  
**Alpha/yr:** 11.9% (+6.4%)  
**WinRate:** 70.0%  
**Hypothesis:** Config B + earnings surprise signal (±8pts, 90d decay, PIT-safe)  
**Verdict:** ✅ IMPROVED

---
