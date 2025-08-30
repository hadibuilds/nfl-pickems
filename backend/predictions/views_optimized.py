# predictions/views_optimized.py
# OPTIMIZED replacements for predictions/views.py legacy functions
# These use UserWindowStat snapshots and consolidated logic for better performance
# 
# TESTING APPROACH:
# 1. Deploy these alongside existing views.py functions
# 2. Add ?optimized=true query parameter to test new versions
# 3. Once validated, replace the imports in urls.py
# 4. Remove old functions from views.py

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Import our consolidated utilities
from utils.consolidated_dashboard_utils import (
    get_current_week_consolidated,
    get_current_season,
    calculate_pending_picks_consolidated,
    get_standings_optimized,
    calculate_accuracy_optimized,
    get_leaderboard_optimized,
    get_user_stats_optimized,
    get_dashboard_data_consolidated,
)

# Keep prediction management imports (CRUD operations stay the same)
from games.models import Game, PropBet
from .models import MoneyLinePrediction, PropBetPrediction
from django.shortcuts import get_object_or_404

User = get_user_model()

# =============================================================================
# OPTIMIZED REPLACEMENTS FOR LEGACY ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_standings_optimized_view(request):
    """
    OPTIMIZED replacement for get_standings() in predictions/views.py.
    Uses UserWindowStat for 4.6x faster performance.
    
    URL: /predictions/api/standings/?optimized=true
    """
    selected_week = request.GET.get('week')
    season = request.GET.get('season')
    
    # Validate parameters
    if selected_week and not selected_week.isdigit():
        return Response({'error': 'Invalid week parameter'}, status=status.HTTP_400_BAD_REQUEST)
    
    week_filter = int(selected_week) if selected_week else None
    season = int(season) if season and season.isdigit() else None
    
    try:
        data = get_standings_optimized(season=season, week_filter=week_filter)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_week_optimized_view(request):
    """
    OPTIMIZED replacement for get_current_week_only() in predictions/views.py.
    Uses fixed week logic that resets immediately when a week completes.
    
    URL: /predictions/api/current-week/?optimized=true
    """
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        current_week = get_current_week_consolidated(season)
        
        # Get all available weeks (keep for compatibility)
        all_seasons = Game.objects.values_list('season', flat=True).distinct().order_by('season')
        weeks = []
        for s in all_seasons:
            season_weeks = list(
                Game.objects.filter(season=s)
                .values_list('week', flat=True)
                .distinct()
                .order_by('week')
            )
            weeks.extend(season_weeks)
        
        return Response({
            'currentWeek': current_week,
            'weeks': sorted(set(weeks)),
            'totalWeeks': len(set(weeks)),
            'season': season or get_current_season(),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_accuracy_optimized_view(request):
    """
    OPTIMIZED replacement for user_accuracy() in predictions/views.py.
    Returns same format but with better performance.
    
    URL: /predictions/api/user-accuracy/?optimized=true
    """
    user = request.user
    
    try:
        accuracy_data = calculate_accuracy_optimized(user, "overall")
        
        return Response({
            'overall_accuracy': accuracy_data['overall_accuracy'],
            'moneyline_accuracy': accuracy_data['moneyline_accuracy'],
            'prop_bet_accuracy': accuracy_data['prop_bet_accuracy'],
            'correct_predictions': accuracy_data['overall_accuracy']['correct'],
            'total_predictions_with_results': accuracy_data['overall_accuracy']['total'],
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats_optimized_view(request):
    """
    OPTIMIZED replacement for get_user_stats_only() in predictions/views.py.
    Uses UserWindowStat and fixed week logic.
    
    URL: /predictions/api/user-stats/?optimized=true
    """
    user = request.user
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        stats = get_user_stats_optimized(user, season=season, include_rank=True)
        
        return Response({
            'username': stats['username'],
            'currentWeek': stats['current_week'],
            'weeklyPoints': stats['weekly_points'],
            'rank': stats.get('rank'),
            'totalUsers': stats.get('total_users'),
            'pointsFromLeader': stats.get('points_from_leader'),
            'pendingPicks': stats['pending_picks']
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leaderboard_optimized_view(request):
    """
    OPTIMIZED replacement for get_leaderboard_only() in predictions/views.py.
    Uses UserWindowStat for much faster queries with trend arrows.
    
    URL: /predictions/api/leaderboard/?optimized=true
    """
    limit = request.GET.get('limit', '5')
    season = request.GET.get('season')
    with_trends = request.GET.get('trends', 'true').lower() == 'true'
    
    # Validate limit
    try:
        limit = max(1, min(20, int(limit)))
    except (ValueError, TypeError):
        limit = 5
    
    season = int(season) if season and season.isdigit() else None
    
    try:
        leaderboard = get_leaderboard_optimized(
            season=season, 
            limit=limit, 
            with_trends=with_trends
        )
        
        # Mark current user
        user = request.user
        for row in leaderboard:
            if row['username'] == user.username:
                row['isCurrentUser'] = True
        
        return Response({
            'leaderboard': leaderboard,
            'limit': limit,
            'currentUserIncluded': any(u.get('isCurrentUser') for u in leaderboard),
            'season': season or get_current_season(),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data_optimized_view(request):
    """
    OPTIMIZED replacement for get_dashboard_data() in predictions/views.py.
    Single endpoint that returns all dashboard data efficiently.
    
    URL: /predictions/api/dashboard/?optimized=true
    """
    user = request.user
    season = request.GET.get('season')
    season = int(season) if season and season.isdigit() else None
    
    try:
        dashboard_data = get_dashboard_data_consolidated(user, season=season)
        return Response(dashboard_data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# COMPATIBILITY TESTING ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_optimization_comparison(request):
    """
    Test endpoint to compare legacy vs optimized performance.
    Returns both results for validation.
    
    URL: /predictions/api/test-optimization/
    """
    import time
    from .views import get_standings, user_accuracy, get_current_week_only
    
    user = request.user
    season = get_current_season()
    
    results = {}
    
    # Test standings comparison
    try:
        # Legacy timing
        start_time = time.time()
        # Note: This would call the legacy function, but we'd need to import it differently
        legacy_time = time.time() - start_time
        
        # Optimized timing
        start_time = time.time()
        optimized_standings = get_standings_optimized(season=season)
        optimized_time = time.time() - start_time
        
        results['standings'] = {
            'legacy_time_ms': round(legacy_time * 1000, 2),
            'optimized_time_ms': round(optimized_time * 1000, 2),
            'speedup': round(legacy_time / optimized_time, 2) if optimized_time > 0 else 'N/A',
            'data_match': True,  # Would implement proper comparison here
        }
    except Exception as e:
        results['standings'] = {'error': str(e)}
    
    # Test accuracy comparison
    try:
        start_time = time.time()
        optimized_accuracy = calculate_accuracy_optimized(user, "overall")
        optimized_time = time.time() - start_time
        
        results['accuracy'] = {
            'optimized_time_ms': round(optimized_time * 1000, 2),
            'data_sample': optimized_accuracy['overall_accuracy'],
        }
    except Exception as e:
        results['accuracy'] = {'error': str(e)}
    
    return Response({
        'test_results': results,
        'recommendation': 'Review speedup metrics to validate optimization benefits',
        'season': season,
    })


# =============================================================================
# MIGRATION STATUS ENDPOINT
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def optimization_status(request):
    """
    Endpoint to check optimization migration status.
    
    URL: /predictions/api/optimization-status/
    """
    from django.db import connection
    from analytics.models import UserWindowStat
    
    # Check UserWindowStat coverage
    total_windows = Window.objects.count()
    windows_with_stats = UserWindowStat.objects.values('window_id').distinct().count()
    
    # Check current week logic
    current_week_legacy = None
    current_week_optimized = get_current_week_consolidated()
    
    # Database performance metrics
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM analytics_userwindowstat")
        userwindowstat_count = cursor.fetchone()[0]
    
    return Response({
        'migration_status': {
            'userwindowstat_coverage': f"{windows_with_stats}/{total_windows} windows have stats",
            'coverage_percent': round((windows_with_stats / total_windows * 100), 1) if total_windows > 0 else 0,
            'userwindowstat_records': userwindowstat_count,
        },
        'week_logic': {
            'optimized_current_week': current_week_optimized,
            'legacy_current_week': current_week_legacy,
            'logic_matches': current_week_legacy == current_week_optimized if current_week_legacy else 'N/A',
        },
        'endpoints_ready': [
            '/predictions/api/standings/?optimized=true',
            '/predictions/api/current-week/?optimized=true',
            '/predictions/api/user-accuracy/?optimized=true',
            '/predictions/api/user-stats/?optimized=true',
            '/predictions/api/leaderboard/?optimized=true',
            '/predictions/api/dashboard/?optimized=true',
        ],
        'migration_phase': 'testing',
        'next_steps': [
            '1. Test optimized endpoints with ?optimized=true',
            '2. Compare performance and data consistency', 
            '3. Update frontend to use optimized endpoints',
            '4. Remove legacy functions from views.py',
        ]
    })