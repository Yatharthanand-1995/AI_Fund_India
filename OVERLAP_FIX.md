# Overlap Fix - Agent Score Boxes Overlapping Buttons

## Issue
The agent score boxes (Fundamentals, Momentum, Quality, Sentiment, Institutional) were overlapping the action buttons ("Add to Watchlist", "Full Analysis", "Compare").

## Root Cause
The `AgentScoresRadar` component was constrained by a fixed height container (`h-52` = 208px) in `InvestmentIdeaCard.tsx`.

The component actually needs:
- Chart: 200px
- Score Summary grid: ~120px (5 colored boxes with padding)
- Agent Details section: variable height
- Margins: 24px between sections

**Total needed: ~350-400px** but only **208px available** → Content overflow

## Fix Applied

**File**: `frontend/src/components/InvestmentIdeaCard.tsx`
**Line**: 187

### Before:
```tsx
<div className="h-52">
  <AgentScoresRadar agentScores={agent_scores} height={200} />
</div>
```

### After:
```tsx
<div>
  <AgentScoresRadar agentScores={agent_scores} height={200} />
</div>
```

## Impact
- ✅ Agent score boxes now render in their proper position
- ✅ No overlap with buttons below
- ✅ Proper vertical spacing maintained
- ✅ Component can render full content naturally

## Testing
Refresh `localhost:3000/ideas` and verify:
- [ ] Colored agent score boxes appear between the radar chart and the confidence bar
- [ ] No overlap with "Add to Watchlist" button
- [ ] All content flows properly top to bottom

---
*Fixed: 2026-02-09*
