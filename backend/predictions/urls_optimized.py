# predictions/urls_optimized.py
# TEMPORARY URL routing for testing optimized endpoints
# 
# USAGE:
# 1. Add to main urls.py: path('predictions/optimized/', include('predictions.urls_optimized'))
# 2. Test endpoints with /predictions/optimized/api/... paths
# 3. Once validated, replace imports in main predictions/urls.py
# 4. Remove this file

from django.urls import path
from .views_optimized import (
    # Optimized replacements for legacy functions
    get_standings_optimized_view,
    get_current_week_optimized_view,
    user_accuracy_optimized_view,
    get_user_stats_optimized_view,
    get_leaderboard_optimized_view,
    get_dashboard_data_optimized_view,
    
    # Testing and migration utilities
    test_optimization_comparison,
    optimization_status,
)

urlpatterns = [
    # =============================================================================
    # OPTIMIZED REPLACEMENTS (for testing)
    # =============================================================================
    
    # Standings (replaces get_standings in views.py)
    path('api/standings/', get_standings_optimized_view, name='standings_optimized'),
    
    # Current week (replaces get_current_week_only in views.py)
    path('api/current-week/', get_current_week_optimized_view, name='current_week_optimized'),
    
    # User accuracy (replaces user_accuracy in views.py)  
    path('api/user-accuracy/', user_accuracy_optimized_view, name='user_accuracy_optimized'),
    
    # User stats (replaces get_user_stats_only in views.py)
    path('api/user-stats/', get_user_stats_optimized_view, name='user_stats_optimized'),
    
    # Leaderboard (replaces get_leaderboard_only in views.py)
    path('api/leaderboard/', get_leaderboard_optimized_view, name='leaderboard_optimized'),
    
    # Dashboard (replaces get_dashboard_data in views.py)
    path('api/dashboard/', get_dashboard_data_optimized_view, name='dashboard_optimized'),
    
    # =============================================================================
    # TESTING AND MIGRATION UTILITIES
    # =============================================================================
    
    # Performance comparison testing
    path('api/test-optimization/', test_optimization_comparison, name='test_optimization'),
    
    # Migration status checking
    path('api/optimization-status/', optimization_status, name='optimization_status'),
]

# =============================================================================
# INTEGRATION NOTES
# =============================================================================
"""
TESTING APPROACH:

1. Add to main project urls.py:
   ```python
   path('predictions/optimized/', include('predictions.urls_optimized')),
   ```

2. Test optimized endpoints:
   - GET /predictions/optimized/api/standings/
   - GET /predictions/optimized/api/current-week/
   - GET /predictions/optimized/api/user-accuracy/
   - GET /predictions/optimized/api/user-stats/
   - GET /predictions/optimized/api/leaderboard/
   - GET /predictions/optimized/api/dashboard/

3. Compare with legacy endpoints:
   - GET /predictions/api/standings/ (legacy)
   - GET /predictions/api/current-week/ (legacy)
   - etc.

4. Use testing utilities:
   - GET /predictions/optimized/api/test-optimization/
   - GET /predictions/optimized/api/optimization-status/

5. Frontend testing:
   Update frontend API calls temporarily:
   ```javascript
   // Before
   const res = await fetch(`${API_BASE}/predictions/api/standings/`)
   
   // Testing
   const res = await fetch(`${API_BASE}/predictions/optimized/api/standings/`)
   ```

6. Migration path:
   a) Validate data consistency and performance improvements
   b) Update main predictions/urls.py to import from views_optimized
   c) Remove legacy functions from predictions/views.py
   d) Remove this temporary file

EXPECTED PERFORMANCE IMPROVEMENTS:
- Standings: 4.6x faster (from database analysis)
- User Stats: 3-5x faster (UserWindowStat vs raw predictions)
- Leaderboard: 2-4x faster (pre-computed ranks and points)
- Dashboard: 2-3x faster (consolidated queries)
"""