# Windowed Ranking System - Complete Implementation 🚀

## What We Built

A **complete windowed ranking system** that tracks user standings across time windows with intelligent trend analysis. Clean separation from your existing analytics, ready for production use.

## Key Features ✅

### 1. **Smart Baseline Handling**
- Everyone starts at rank 12 (worst possible)
- **No trend arrows shown for W1** (avoids "everyone trending up" problem)
- Clean, professional first impression for your family/friends

### 2. **Window-Based Architecture** 
- Time windows: `YYYY-MM-DD:morning|afternoon|late` (PT timezone)
- Dense ranking (1,2,2,3) with consistent tie-breaking
- Automatic trend calculation between consecutive windows

### 3. **Correction-Friendly Design**
- Change early window → recompute all downstream windows automatically
- No special cases, just clean prefix-sum recalculation
- Maintains data integrity through corrections

### 4. **Performance Optimized**
- Materialized views for fast queries (PostgreSQL)
- Efficient bulk operations for data processing
- Proper indexes for quick leaderboard access

## File Structure

```
analytics/
├── models.py (+ UserWindowDeltas, UserWindowCumulative)
├── services/windowed_rankings.py (core business logic)
├── views.py (+ windowed API endpoints)  
├── urls.py (+ windowed routes)
├── management/commands/backfill_windowed_rankings.py
└── migrations/
    ├── 0003_windowed_ranking_system.py
    └── 0004_windowed_materialized_views.py
```

## API Endpoints

### **For Homepage** (Top-3 with trends)
```
GET /analytics/api/windowed-top3/
→ {items: [{username, rank, total_points, trend, rank_change}...]}
```

### **For Standings Page** (All 12 users with trends) 
```
GET /analytics/api/windowed-standings/
→ {standings: [{username, rank, total_points, trend, rank_change_display}...]}
```

### **For User Profile** (Individual history)
```
GET /analytics/api/user-windowed-history/
→ {history: [{window_key, rank, total_points, trend}...]}
```

## Setup Instructions

### 1. **Run Migrations**
```bash
python manage.py migrate analytics
```

### 2. **Backfill Historical Data**
```bash
# Dry run first
python manage.py backfill_windowed_rankings --season 2025 --dry-run

# Actually backfill
python manage.py backfill_windowed_rankings --season 2025
```

### 3. **Update Frontend**
Replace your current leaderboard calls:
```javascript
// OLD
const response = await fetch('/analytics/api/home-top3/');

// NEW  
const response = await fetch('/analytics/api/windowed-top3/');
// Same data structure, but with proper trend arrows!
```

## Data Flow

```
1. Games complete → window_key generated (PT timezone)
2. Delta calculation → points earned per user per window  
3. Cumulative calculation → running totals + dense ranks
4. Trend calculation → compare to previous window rank
5. Store results → fast API queries
6. Corrections → recompute affected windows forward
```

## Why This Is Better

**Before:** Messy mix of realtime + snapshots, arbitrary game streaks, confusing trend logic

**After:** Clean windowed checkpoints, meaningful rank-based achievements, correction-friendly architecture

### **Concrete Improvements:**
- ✅ **Trend arrows make sense** - based on actual rank movement between windows
- ✅ **No confusing "everyone up" after W1** - trends suppressed until W2
- ✅ **Corrections work cleanly** - change early data → downstream updates automatically
- ✅ **All 12 users tracked** - complete standings with movement for everyone
- ✅ **Performance optimized** - materialized views for fast queries
- ✅ **Separation of concerns** - windowed standings vs broader analytics

## Next Steps

### **Immediate (to get running):**
1. Run migrations to create tables
2. Backfill historical data with management command
3. Update frontend to use new windowed endpoints

### **Future Enhancements:**
1. **Window closing automation** - auto-process when all games complete
2. **Correction event tracking** - full audit trail for late changes  
3. **Advanced analytics** - build insights on top of windowed foundation
4. **Multi-season support** - expand beyond current year

## Frontend Integration

Your existing homepage code will work with minimal changes:

```javascript
// Before
const {items} = await fetch('/analytics/api/home-top3/').then(r => r.json());

// After  
const {items} = await fetch('/analytics/api/windowed-top3/').then(r => r.json());

// Same structure, but now with proper trends:
items.forEach(user => {
  const trendArrow = user.trend === 'up' ? '↗️' : 
                    user.trend === 'down' ? '↘️' : 
                    user.trend === 'same' ? '→' : '';
  // Only shows arrows when meaningful (after W1)
});
```

## The Foundation Is Set 🎯

This windowed system gives you a **solid foundation** for all future analytics:

- **Clean data model** that handles corrections gracefully
- **Time-based analysis** that makes sense to users
- **Performance optimized** for your 12-person league scale  
- **Extensible architecture** for building advanced insights

Your analytics app now has a proper **standings engine** that can power both simple leaderboards and sophisticated performance analysis. The messy realtime/snapshot hybrid is replaced with a clean, deterministic system that your users will understand and trust.

**Ready to ship!** 🚀