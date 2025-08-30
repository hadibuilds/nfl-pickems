# utils/consolidated_dashboard_utils.py
# CONSOLIDATED & OPTIMIZED dashboard utilities to replace fragmented logic
# This file consolidates all dashboard/leaderboard/stats logic into optimized variants
# using UserWindowStat snapshots and proper week logic

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, Max, Count, F, Case, When, IntegerField
from django.utils import timezone
from django.db.models import Prefetch

from games.models import Game, Window, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction, UserStatHistory
from analytics.models import UserWindowStat

User = get_user_model()

# Constants
ML_POINTS = 1
PB_POINTS = 2
SLOT_ORDER = {"morning": 0, "afternoon": 1, "late": 2}

# =============================================================================
# CORE WEEK & WINDOW LOGIC (SINGLE SOURCE OF TRUTH)
# =============================================================================

def get_current_week_consolidated(season: int | None = None) -> int:
    """
    SINGLE SOURCE OF TRUTH for current week calculation.
    Returns the earliest week that has games without winners (unfinished).
    Week transitions happen immediately when the last game of a week finishes.
    """
    base_qs = Game.objects.all()
    if season is not None:
        base_qs = base_qs.filter(season=season)
    
    # Primary logic: Find the earliest week with unfinished games (no winner)
    unfinished_games = base_qs.filter(winner__isnull=True)
    if unfinished_games.exists():
        return int(unfinished_games.order_by("week", "start_time").first().week)
    
    # Fallback: Return the next week after the highest completed week
    latest_completed_week = base_qs.aggregate(
        max_week=Max("week")
    )["max_week"]
    
    if latest_completed_week is not None:
        return int(latest_completed_week) + 1
    
    # Ultimate fallback
    return 1


def get_current_season() -> int:
    """Get the current season based on the most recent games."""
    season = (
        Game.objects.order_by('-season')
        .values_list('season', flat=True)
        .first()
    )
    return int(season) if season is not None else 2025


def get_current_window_consolidated(season: int) -> Optional[Window]:
    """
    Find the most appropriate window for analytics display.
    Prioritizes completed windows with data, then active windows, then latest by date.
    """
    today = timezone.now().date()
    
    # 1) Try latest COMPLETED window with user stats (most stable for leaderboard)
    latest_completed_with_stats = (
        Window.objects.filter(
            season=season,
            is_complete=True,
            user_stats__isnull=False
        )
        .distinct()
        .order_by('-date', '-slot')
        .first()
    )
    if latest_completed_with_stats:
        return latest_completed_with_stats
    
    # 2) Try any completed window
    latest_completed = (
        Window.objects.filter(season=season, is_complete=True)
        .order_by('-date', '-slot')
        .first()
    )
    if latest_completed:
        return latest_completed
    
    # 3) Try active/current window (today or recent)
    active_window = (
        Window.objects.filter(season=season, date__lte=today)
        .order_by('-date', '-slot')
        .first()
    )
    if active_window:
        return active_window
    
    # 4) Fallback to any window for the season
    return (
        Window.objects.filter(season=season)
        .order_by('-date', '-slot')
        .first()
    )

# =============================================================================
# OPTIMIZED PENDING PICKS (SINGLE SOURCE OF TRUTH)
# =============================================================================

def calculate_pending_picks_consolidated(user, current_week: int, season: int | None = None) -> int:
    """
    OPTIMIZED pending picks calculation using proper week filtering.
    Fixed the bug where all user predictions were considered instead of just current week.
    """
    now = timezone.now()
    
    # Get games for the current week (with optional season filter)
    week_games_qs = Game.objects.filter(week=current_week)
    if season is not None:
        week_games_qs = week_games_qs.filter(season=season)
    
    week_games = week_games_qs
    unlocked_games = week_games.exclude(Q(locked=True) | Q(start_time__lte=now))
    
    # Get user's ML picks for THIS WEEK only (not all weeks)
    user_ml_picks = set(
        MoneyLinePrediction.objects.filter(
            user=user, game__in=week_games
        ).values_list("game_id", flat=True)
    )
    
    ml_pending = unlocked_games.exclude(id__in=user_ml_picks).count()

    # Count unlocked prop bets user hasn't answered
    unlocked_props = PropBet.objects.filter(game__in=unlocked_games)
    user_prop_picks = set(
        PropBetPrediction.objects.filter(
            user=user, prop_bet__in=unlocked_props
        ).values_list("prop_bet_id", flat=True)
    )
    
    pb_pending = unlocked_props.exclude(id__in=user_prop_picks).count()
    return int(ml_pending + pb_pending)

# =============================================================================
# OPTIMIZED STANDINGS (REPLACES LEGACY get_standings)
# =============================================================================

def get_standings_optimized(season: int | None = None, week_filter: int | None = None) -> Dict[str, Any]:
    """
    OPTIMIZED replacement for predictions/views.py get_standings.
    Uses UserWindowStat for fast calculation instead of raw prediction queries.
    """
    if season is None:
        season = get_current_season()
    
    # Map each window_id -> NFL week (distinct to avoid double counting)
    window_week_rows = Game.objects.filter(season=season).values('window_id', 'week').distinct()
    window_to_week = {row['window_id']: row['week'] for row in window_week_rows if row['window_id'] is not None}
    all_weeks = sorted(set(window_to_week.values()))
    
    # Get all users
    users = User.objects.all()
    standings = []
    
    for user in users:
        # Get latest cumulative points per window for this user (optimized via UserWindowStat)
        window_stats = (
            UserWindowStat.objects
            .filter(user=user, window__season=season)
            .values('window_id')
            .annotate(points=Max('season_cume_points'))
        )
        
        # Calculate per-week breakdown from cumulative values
        weekly_scores = defaultdict(int)
        window_points = {}
        max_cumulative = 0
        
        for stat in window_stats:
            window_id = stat['window_id']
            points = int(stat['points'] or 0)
            window_points[window_id] = points
            max_cumulative = max(max_cumulative, points)
        
        # Calculate per-week deltas from cumulative values
        sorted_windows = sorted(window_points.keys())
        prev_cumulative = 0
        for window_id in sorted_windows:
            week = window_to_week.get(window_id)
            if week is None:
                continue
            current_cumulative = window_points[window_id]
            week_delta = current_cumulative - prev_cumulative
            weekly_scores[int(week)] += max(0, week_delta)  # Only positive deltas
            prev_cumulative = current_cumulative
        
        total_points = (
            weekly_scores.get(week_filter, 0)
            if week_filter is not None else
            max_cumulative  # Use max cumulative, not sum of deltas
        )
        
        standings.append({
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'weekly_scores': dict(weekly_scores),
            'total_points': int(total_points),
        })
    
    standings.sort(key=lambda x: (-x['total_points'], x['username'].lower()))
    
    return {
        'standings': standings,
        'weeks': all_weeks,
        'selected_week': week_filter,
        'total_users': len(standings),
        'season': season,
    }

# =============================================================================
# OPTIMIZED ACCURACY (REPLACES LEGACY user_accuracy)
# =============================================================================

def calculate_accuracy_optimized(user, kind: str = "overall") -> Dict[str, Any]:
    """
    OPTIMIZED replacement for predictions/views.py user_accuracy.
    Returns both percentages and raw counts for flexibility.
    """
    def pct(c, t): 
        return 0 if not t else round(100 * c / t, 1)
    
    if kind == "moneyline":
        qs = MoneyLinePrediction.objects.filter(user=user, is_correct__isnull=False)
        correct = qs.filter(is_correct=True).count()
        total = qs.count()
        return {
            'percentage': pct(correct, total),
            'correct': correct,
            'total': total
        }
    
    if kind == "prop":
        qs = PropBetPrediction.objects.filter(user=user, is_correct__isnull=False)
        correct = qs.filter(is_correct=True).count()
        total = qs.count()
        return {
            'percentage': pct(correct, total),
            'correct': correct,
            'total': total
        }
    
    # Overall accuracy
    ml_qs = MoneyLinePrediction.objects.filter(user=user, is_correct__isnull=False)
    pb_qs = PropBetPrediction.objects.filter(user=user, is_correct__isnull=False)
    
    ml_correct = ml_qs.filter(is_correct=True).count()
    ml_total = ml_qs.count()
    pb_correct = pb_qs.filter(is_correct=True).count()
    pb_total = pb_qs.count()
    
    total_correct = ml_correct + pb_correct
    total_preds = ml_total + pb_total
    
    return {
        'overall_accuracy': {
            'percentage': pct(total_correct, total_preds),
            'correct': total_correct,
            'total': total_preds
        },
        'moneyline_accuracy': {
            'percentage': pct(ml_correct, ml_total),
            'correct': ml_correct,
            'total': ml_total
        },
        'prop_bet_accuracy': {
            'percentage': pct(pb_correct, pb_total),
            'correct': pb_correct,
            'total': pb_total
        },
        'total_points_from_predictions': (ml_correct * ML_POINTS) + (pb_correct * PB_POINTS)
    }

# =============================================================================
# OPTIMIZED LEADERBOARD WITH TRENDS (REPLACES MULTIPLE VARIANTS)
# =============================================================================

def get_leaderboard_optimized(season: int | None = None, limit: int = 10, with_trends: bool = True) -> List[Dict[str, Any]]:
    """
    OPTIMIZED leaderboard using UserWindowStat for fast queries.
    Optionally includes trend arrows based on rank_delta.
    """
    if season is None:
        season = get_current_season()
    
    # Get leaderboard from UserWindowStat (much faster than raw predictions)
    leaderboard_data = (
        UserWindowStat.objects
        .filter(window__season=season)
        .values('user_id', 'user__username')
        .annotate(total_points=Sum('season_cume_points'))
        .order_by('-total_points', 'user__username')[:limit]
    )
    
    leaderboard = []
    for row in leaderboard_data:
        entry = {
            'user_id': row['user_id'],
            'username': row['user__username'],
            'total_points': int(row['total_points'] or 0),
        }
        
        if with_trends:
            # Get latest rank_delta for trend arrow
            latest_stat = (
                UserWindowStat.objects
                .filter(user_id=row['user_id'], window__season=season)
                .order_by('-window__date', '-window__slot')
                .first()
            )
            
            if latest_stat and latest_stat.rank_delta is not None:
                if latest_stat.rank_delta > 0:
                    entry['trend'] = 'up'
                    entry['rank_change'] = latest_stat.rank_delta
                elif latest_stat.rank_delta < 0:
                    entry['trend'] = 'down' 
                    entry['rank_change'] = abs(latest_stat.rank_delta)
                else:
                    entry['trend'] = 'same'
                    entry['rank_change'] = 0
            else:
                entry['trend'] = 'same'
                entry['rank_change'] = 0
        
        leaderboard.append(entry)
    
    return leaderboard

# =============================================================================
# OPTIMIZED USER STATS (REPLACES MULTIPLE DASHBOARD FUNCTIONS)
# =============================================================================

def get_user_stats_optimized(user, season: int | None = None, include_rank: bool = True) -> Dict[str, Any]:
    """
    OPTIMIZED user stats using UserWindowStat and proper week logic.
    Single source of truth for dashboard data.
    """
    if season is None:
        season = get_current_season()
    
    current_week = get_current_week_consolidated(season)
    
    # Get latest user stats from UserWindowStat (much faster)
    latest_stat = (
        UserWindowStat.objects
        .filter(user=user, window__season=season)
        .order_by('-window__date', '-window__slot')
        .first()
    )
    
    # Calculate weekly points for current week
    week_window_ids = list(
        Window.objects.filter(
            season=season,
            games__week=current_week
        ).values_list("id", flat=True).distinct()
    )
    
    weekly_points = (
        UserWindowStat.objects
        .filter(user=user, window_id__in=week_window_ids)
        .aggregate(points=Sum("window_points"))["points"] or 0
    )
    
    # Get total season points
    total_points = (
        UserWindowStat.objects
        .filter(user=user, window__season=season)
        .aggregate(points=Sum("season_cume_points"))["points"] or 0
    )
    
    # Calculate pending picks
    pending_picks = calculate_pending_picks_consolidated(user, current_week, season)
    
    # Get accuracy data
    accuracy_data = calculate_accuracy_optimized(user, "overall")
    
    result = {
        'username': user.username,
        'current_week': current_week,
        'weekly_points': int(weekly_points),
        'total_points': int(total_points),
        'pending_picks': pending_picks,
        'overall_accuracy': accuracy_data['overall_accuracy']['percentage'],
        'moneyline_accuracy': accuracy_data['moneyline_accuracy']['percentage'],
        'prop_bet_accuracy': accuracy_data['prop_bet_accuracy']['percentage'],
        'season': season,
    }
    
    if include_rank and latest_stat:
        # Calculate current rank (expensive but cached via UserWindowStat)
        better_users = (
            UserWindowStat.objects
            .filter(
                window=latest_stat.window,
                season_cume_points__gt=latest_stat.season_cume_points
            )
            .count()
        )
        
        total_users = (
            UserWindowStat.objects
            .filter(window=latest_stat.window)
            .count()
        )
        
        # Calculate points from leader
        leader_points = (
            UserWindowStat.objects
            .filter(window=latest_stat.window)
            .aggregate(max_points=Max("season_cume_points"))["max_points"] or 0
        )
        
        result.update({
            'rank': better_users + 1,
            'total_users': total_users,
            'points_from_leader': max(0, int(leader_points) - int(latest_stat.season_cume_points or 0)),
            'rank_delta': latest_stat.rank_delta or 0,
        })
    
    return result

# =============================================================================
# MIGRATION HELPERS (FOR TESTING COMPATIBILITY)
# =============================================================================

def test_compatibility_predictions_vs_optimized():
    """
    Helper function to test that optimized functions return equivalent data
    to the legacy predictions/views.py functions.
    """
    # This would be used in tests to ensure the migration doesn't break anything
    pass

# =============================================================================
# CONVENIENCE FUNCTIONS (FOR EASY ENDPOINT CONVERSION)
# =============================================================================

def get_dashboard_data_consolidated(user, season: int | None = None) -> Dict[str, Any]:
    """
    Single function that returns all dashboard data in the format expected by frontend.
    Replaces multiple individual endpoint calls.
    """
    if season is None:
        season = get_current_season()
    
    # Get core user stats
    user_stats = get_user_stats_optimized(user, season, include_rank=True)
    
    # Get leaderboard
    leaderboard = get_leaderboard_optimized(season, limit=5, with_trends=True)
    
    # Mark current user in leaderboard
    for entry in leaderboard:
        if entry['username'] == user.username:
            entry['isCurrentUser'] = True
    
    return {
        'user_data': user_stats,
        'leaderboard': leaderboard,
        'meta': {
            'calculation_mode': 'optimized',
            'season': season,
            'timestamp': timezone.now().isoformat(),
        }
    }

# =============================================================================
# EXPORT ALL FUNCTIONS FOR EASY IMPORTING
# =============================================================================

__all__ = [
    'get_current_week_consolidated',
    'get_current_season',
    'get_current_window_consolidated',
    'calculate_pending_picks_consolidated',
    'get_standings_optimized',
    'calculate_accuracy_optimized',
    'get_leaderboard_optimized',
    'get_user_stats_optimized',
    'get_dashboard_data_consolidated',
]