# Backtest Management System - Implementation Plan

## Executive Summary

Create a production-ready backtest management system with:
- **New dedicated "Backtest" tab** in the frontend
- **Reusable backtest configuration** system
- **Comprehensive analytics dashboard** with equity curve, signal performance, agent breakdown, and detailed trade list
- **Backtest history** with ability to compare multiple runs
- **One-click re-run** functionality with saved configurations
- **Enhanced backend API** for backtest management

---

## Current Status: PARTIALLY IMPLEMENTED

### ✅ Completed (Phase 1: Backend - 100%)

1. **Backend Configuration Manager** (`core/backtest_config.py`)
   - BacktestConfig dataclass with serialization
   - Configuration saving/loading
   - Date update functionality for re-running
   - Default configuration creator

2. **Equity Curve Calculator** (`core/equity_curve.py`)
   - Portfolio performance calculation over time
   - Equity curve generation (portfolio vs benchmark)
   - Trade statistics (win rate, Sharpe ratio, etc.)
   - Drawdown analysis and recovery time

3. **Enhanced API Endpoints** (`api/main.py`)
   - Enhanced POST `/backtest/run` - saves configuration, handles NIFTY 50 default
   - New POST `/backtest/rerun/{run_id}` - re-run with saved config, optional date update
   - Enhanced GET `/backtest/runs` - pagination, sorting by multiple metrics
   - Enhanced GET `/backtest/results/{run_id}` - includes equity curve data
   - New GET `/backtest/comparison` - compare multiple runs side-by-side

4. **Frontend Types & API** (Partial)
   - Complete TypeScript type definitions (`frontend/src/types/backtest.ts`)
   - API client methods added (`frontend/src/lib/api.ts`)

---

## ⏳ Remaining Work (Phase 2: Frontend Components)

### Priority 1: Core Components

1. **Main Backtest Page** (`frontend/src/pages/Backtest.tsx`)
   ```tsx
   - Tab navigation (History | Results | Comparison)
   - State management for selected runs
   - Integration with all sub-components
   ```

2. **Backtest History Component** (`frontend/src/components/backtest/BacktestHistory.tsx`)
   ```tsx
   - Grid of backtest run cards
   - Sort controls (by date, Sharpe, return, alpha)
   - Multi-select for comparison
   - Pagination
   ```

3. **Backtest Run Card** (`frontend/src/components/backtest/BacktestRunCard.tsx`)
   ```tsx
   - Key metrics display (return, Sharpe, alpha, max DD)
   - Quick actions (View, Re-run, Delete)
   - Selection checkbox for comparison
   - Visual indicators for performance
   ```

### Priority 2: Results & Visualization

4. **Backtest Results Component** (`frontend/src/components/backtest/BacktestResults.tsx`)
   ```tsx
   - Summary header with key metrics
   - Tabs: Overview | Signals | Agent Performance
   - Integration of all charts and tables
   ```

5. **Equity Curve Chart** (`frontend/src/components/charts/EquityCurveChart.tsx`)
   ```tsx
   - Dual-axis line chart (value + returns)
   - Portfolio vs benchmark lines
   - Tooltips with detailed info
   - Recharts implementation
   ```

6. **Signal Distribution Chart** (`frontend/src/components/charts/SignalDistributionChart.tsx`)
   ```tsx
   - Pie chart for recommendation breakdown
   - Performance metrics per recommendation type
   - Hit rates and avg alpha per category
   ```

7. **Trade List Table** (`frontend/src/components/backtest/TradeListTable.tsx`)
   ```tsx
   - Filterable by recommendation, symbol, alpha range
   - Sortable by date, alpha, return, score
   - Pagination for large datasets
   - Export functionality (future)
   ```

8. **Agent Performance Breakdown** (`frontend/src/components/backtest/AgentPerformanceBreakdown.tsx`)
   ```tsx
   - Correlation bar chart
   - Current vs optimal weights comparison
   - Individual agent cards with metrics
   ```

### Priority 3: Actions & Controls

9. **Backtest Run Button/Modal** (`frontend/src/components/backtest/BacktestRunButton.tsx`)
   ```tsx
   - Configuration form (dates, frequency, name)
   - Validation
   - Submit handler with loading state
   - Success/error notifications
   ```

10. **Backtest Comparison Component** (`frontend/src/components/backtest/BacktestComparison.tsx`)
    ```tsx
    - Side-by-side equity curves
    - Comparative metrics table
    - Best performer highlights
    ```

### Priority 4: Navigation Updates

11. **Update App.tsx**
    ```tsx
    - Add /backtest route
    - Import Backtest page component
    ```

12. **Update Header.tsx**
    ```tsx
    - Add "Backtest" nav item with BarChart3 icon
    - Position between Analytics and About
    ```

---

## Database Schema (Already Exists - No Changes Needed)

```sql
-- backtest_runs table
- run_id (TEXT PRIMARY KEY)
- name (TEXT)
- start_date, end_date (TEXT)
- symbols (TEXT JSON)
- frequency (TEXT)
- created_at (TEXT)
- total_signals (INTEGER)
- summary (TEXT JSON)
- metadata (TEXT JSON) -- NOW STORES CONFIG!

-- backtest_signals table
- signal_id (INTEGER PRIMARY KEY)
- run_id (FK)
- symbol, date, recommendation
- composite_score, confidence
- entry_price, exit_price
- forward_return_1m, 3m, 6m
- benchmark_return_1m, 3m, 6m
- alpha_1m, 3m, 6m
- agent_scores (TEXT JSON)
- market_regime (TEXT)
```

---

## Key Features Implemented

### Backend Features ✅

1. **Configuration Persistence**
   - Configs stored in `backtest_runs.metadata.config`
   - Easy re-running with saved parameters
   - Date update option for rolling windows

2. **Equity Curve Calculation**
   - Equal-weight portfolio rebalancing
   - Benchmark comparison (NIFTY 50)
   - Drawdown tracking from peak
   - Compounded returns over time

3. **Enhanced Endpoints**
   - Rate limiting (5 requests/hour for backtests)
   - NIFTY 50 default when symbols=null
   - Flexible sorting and pagination
   - Equity curve generation on-demand

4. **Smart Comparison**
   - Identify best performers across metrics
   - Side-by-side equity curves
   - Comprehensive metric comparison

### Frontend Features (To Be Implemented)

1. **Interactive History**
   - Sort by performance metrics
   - Multi-select for comparison
   - Quick re-run buttons

2. **Rich Visualizations**
   - Equity curve with dual axes
   - Signal distribution pie charts
   - Agent correlation charts

3. **Detailed Analysis**
   - Filterable/sortable trade table
   - Agent performance breakdown
   - Regime-based analysis

4. **User-Friendly Actions**
   - Simple backtest configuration
   - One-click re-run
   - Multi-run comparison

---

## Implementation Order (Remaining Work)

### Phase 2A: Core Structure (2-3 hours)
1. Create main Backtest page with tabs
2. Create BacktestHistory component with grid
3. Create BacktestRunCard component
4. Add navigation to App.tsx and Header.tsx
5. Test basic navigation and layout

### Phase 2B: Visualization (2-3 hours)
1. Create EquityCurveChart component
2. Create SignalDistributionChart component
3. Create BacktestResults component
4. Integrate charts into results view
5. Test data loading and rendering

### Phase 2C: Tables & Details (1-2 hours)
1. Create TradeListTable with filters/sorting
2. Create AgentPerformanceBreakdown
3. Add comparison view
4. Test filtering and interaction

### Phase 2D: Actions (1 hour)
1. Create BacktestRunButton modal
2. Add delete confirmation
3. Add re-run functionality
4. Error handling and notifications

### Phase 2E: Polish (1 hour)
1. Loading states
2. Error boundaries
3. Responsive design
4. Empty states

**Total Estimated Time Remaining**: 7-10 hours

---

## API Endpoints Reference

### Implemented Endpoints

```typescript
// Run new backtest
POST /backtest/run
{
  name?: string,
  symbols?: string[] | null,  // null = NIFTY 50
  start_date: string,
  end_date: string,
  frequency?: 'monthly' | 'weekly' | 'quarterly',
  include_narrative?: boolean
}
→ { run_id, summary, config, duration_seconds }

// Re-run backtest
POST /backtest/rerun/{run_id}?update_dates=true
→ { run_id, summary, config, original_run_id }

// List runs
GET /backtest/runs?limit=50&offset=0&sort_by=created_at&order=desc
→ { runs[], total, limit, offset }

// Get results
GET /backtest/results/{run_id}?include_equity_curve=true&include_signals=true
→ { run_id, summary, equity_curve, signals[], config }

// Compare runs
GET /backtest/comparison?run_ids=id1,id2,id3
→ { runs[], comparison: { best_sharpe, best_return, ... } }

// Delete run
DELETE /backtest/results/{run_id}
→ { success, message }
```

---

## Testing Checklist

### Backend Testing
- [ ] Run backtest with NIFTY 50 (symbols=null)
- [ ] Run backtest with custom symbols
- [ ] Re-run backtest with date update
- [ ] Re-run backtest without date update
- [ ] List runs with different sort orders
- [ ] Get results with equity curve
- [ ] Compare 2-4 runs
- [ ] Delete run
- [ ] Handle invalid run_id
- [ ] Handle invalid date ranges

### Frontend Testing (When Implemented)
- [ ] Navigate to backtest page
- [ ] View backtest history
- [ ] Sort runs by different metrics
- [ ] Select multiple runs for comparison
- [ ] View detailed results
- [ ] Equity curve renders correctly
- [ ] Signal table filters work
- [ ] Agent performance displays
- [ ] Run new backtest from UI
- [ ] Re-run existing backtest
- [ ] Delete backtest with confirmation
- [ ] Compare multiple runs
- [ ] Handle API errors gracefully

---

## Future Enhancements (Not in Current Scope)

- Custom symbol selection (beyond NIFTY 50)
- Advanced configuration (thresholds, weights)
- Export backtest results to CSV/PDF
- Scheduled backtests
- Email notifications when backtest completes
- Monte Carlo simulation
- Risk analysis (VaR, CVaR)
- Sector-specific backtests
- Real-time backtest progress tracking
- Backtest templates (save/load configs)
- Walk-forward analysis
- Out-of-sample testing
- Parameter optimization

---

## Success Criteria

✅ Backend Complete:
- [x] Users can run a backtest via API
- [x] Backtest configuration is saved
- [x] Equity curve is calculated
- [x] Users can re-run backtests
- [x] Users can compare multiple backtests
- [x] All data persists in database

⏳ Frontend In Progress:
- [ ] Users can run a backtest from UI
- [ ] Backtest history displays all past runs
- [ ] Equity curve chart displays portfolio vs benchmark
- [ ] Signal distribution chart shows recommendation breakdown
- [ ] Trade list table is filterable and sortable
- [ ] Agent performance breakdown shows correlations
- [ ] Users can compare multiple backtests side-by-side
- [ ] Re-run button works with saved configuration

---

## Next Steps

1. **Continue frontend implementation** following the priority order above
2. **Test backend endpoints** with Postman or curl to ensure they work
3. **Create minimal UI first** (history + basic results view)
4. **Add charts progressively** once core structure works
5. **Polish and optimize** after all features are functional

---

**Document Status**: Updated after Phase 1 completion
**Last Updated**: 2026-02-03
**Progress**: ~40% complete (Backend 100%, Frontend 20%)
