# Comprehensive Test Plan

## Phase 1: Backend API Testing

### Core APIs
- [ ] GET /health - System health
- [ ] GET /market/regime - Market regime data
- [ ] POST /analyze - Single stock analysis
- [ ] GET /portfolio/top-picks - Top picks
- [ ] POST /compare - Stock comparison
- [ ] GET /analytics/sectors - Sector analytics
- [ ] GET /analytics/system - System analytics
- [ ] GET /stocks/universe - Stock universe

### New/Modified APIs
- [ ] POST /compare - Fixed bug (body → request)
- [ ] Verify compare returns data correctly

## Phase 2: Frontend Page Testing

### Existing Pages
- [ ] / (Dashboard) - Loads without errors
- [ ] /ideas - IDEAS page loads, shows stocks
- [ ] /watchlist - Portfolio tracking works
- [ ] /sectors - Sector analysis loads
- [ ] /about - About page loads

### New Pages (Session 1)
- [ ] /backtest - Backtest UI loads
- [ ] /system - System health dashboard loads

### New Pages (This Session)
- [ ] /screener - Screener loads, filters work
- [ ] /compare - Comparison loads, compare works
- [ ] /analytics - Analytics tabs work
- [ ] /suggestions - Suggestions loads, generates recommendations

## Phase 3: Feature Testing

### Stock Screener
- [ ] Page loads without errors
- [ ] Filters sidebar shows
- [ ] Can apply filters (score, recommendation, agents)
- [ ] Results display in table/cards
- [ ] Export CSV works
- [ ] Presets load and save

### Stock Comparison
- [ ] Can add 2-5 stocks
- [ ] Compare button works
- [ ] Comparison table shows with winner highlighting
- [ ] Charts display (agent scores, returns, radar)
- [ ] Summary shows best/worst
- [ ] Export CSV works

### Advanced Analytics
- [ ] Portfolio tab loads (with watchlist data)
- [ ] Agent Performance tab loads
- [ ] Sector Analysis tab loads
- [ ] System Metrics tab loads
- [ ] Charts render correctly
- [ ] Tables show data

### Smart Suggestions
- [ ] Page loads
- [ ] Generates suggestions from watchlist
- [ ] Shows investment profile
- [ ] Category filters work (All, For You, Diversify, Trending)
- [ ] Suggestion cards show reasons
- [ ] Add to watchlist works
- [ ] View details works

## Phase 4: Integration Testing

### Navigation
- [ ] All nav links work
- [ ] Active page highlighted
- [ ] No broken links

### Watchlist Integration
- [ ] Add stocks to watchlist
- [ ] Remove from watchlist
- [ ] Watchlist count badge updates
- [ ] Analytics uses watchlist data
- [ ] Suggestions uses watchlist data

### State Management
- [ ] Watchlist persists
- [ ] Comparison stocks persist
- [ ] Cache works

### Error Handling
- [ ] API errors show user-friendly messages
- [ ] Loading states show
- [ ] Empty states show correctly

## Phase 5: Performance & Console

### Console Errors
- [ ] No React errors
- [ ] No TypeScript errors
- [ ] No API errors (except expected 404s)
- [ ] No warning spam

### Performance
- [ ] Pages load in reasonable time
- [ ] Charts render smoothly
- [ ] No memory leaks (check with multiple navigations)

## Phase 6: Data Quality

### API Responses
- [ ] Stock data has all required fields
- [ ] Agent scores present
- [ ] Metrics present
- [ ] No null/undefined errors

### Calculations
- [ ] Scores calculated correctly
- [ ] Returns displayed correctly
- [ ] Percentages formatted correctly
- [ ] Winner highlighting correct
