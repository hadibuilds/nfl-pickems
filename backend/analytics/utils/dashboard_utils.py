# analytics/utils/dashboard_utils.py - CRITICAL FIXES: Remove duplicates, fix imports

from django.contrib.auth import get_user_model
from django.db import connection
from ..models import (
    Prediction, PropBetPrediction, UserStatHistory, UserSeasonTotals
)
from games.models import Game, PropBet

User = get_user_model()

# CRITICAL FIX: Consolidated import handling - no more try/catch chaos
try:
    from .trend_utils import (
        get_completed_weeks,
        calculate_user_points_by_week,
        calculate_user_rank_by_week,
        get_user_rank_trend,
        get_user_performance_trend,
        get_user_weekly_analytics,
    )
    TREND_UTILS_AVAILABLE = True
except ImportError as e:
    # NOTE: If trend_utils missing, realtime calculations will be basic
    print(f"Warning: trend_utils not available: {e}")
    TREND_UTILS_AVAILABLE = False

from .ranking_utils import assign_dense_ranks

def get_current_week():
    """Return the first week that is not fully complete; if all done, return last week."""
    all_weeks = Game.objects.values_list('week', flat=True).distinct().order_by('week')
    for week in all_weeks:
        wg = Game.objects.filter(week=week)
        if wg.exists() and wg.filter(winner__isnull=False).count() < wg.count():
            return week
    return all_weeks.last() if all_weeks else 1

def _refresh_mv_if_needed():
    """CRITICAL: Refresh materialized view for accurate calculations"""
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_season_totals_mv;")

# ============================================================================
# CORE CALCULATION FUNCTIONS (consolidated, no duplicates)
# ============================================================================

def calculate_live_stats(user, current_week):
    """Calculate current week's live performance"""
    current_week_games = Game.objects.filter(week=current_week)
    completed_current = current_week_games.filter(winner__isnull=False)

    week_preds = Prediction.objects.filter(user=user, game__in=completed_current)
    week_props = PropBetPrediction.objects.filter(
        user=user, prop_bet__game__in=completed_current, is_correct__isnull=False
    )

    game_correct = week_preds.filter(is_correct=True).count()
    prop_correct = week_props.filter(is_correct=True).count()
    return {
        'weekly_points': game_correct + (prop_correct * 2),
        'game_correct': game_correct,
        'prop_correct': prop_correct,
    }

def calculate_current_accuracy(user, kind):
    """Calculate accuracy by type"""
    completed = Game.objects.filter(winner__isnull=False)
    if kind == 'overall':
        gp = Prediction.objects.filter(user=user, game__in=completed)
        pp = PropBetPrediction.objects.filter(user=user, prop_bet__game__in=completed, is_correct__isnull=False)
        correct = gp.filter(is_correct=True).count() + pp.filter(is_correct=True).count()
        total = gp.count() + pp.count()
    elif kind == 'moneyline':
        gp = Prediction.objects.filter(user=user, game__in=completed)
        correct, total = gp.filter(is_correct=True).count(), gp.count()
    else:  # 'prop'
        pp = PropBetPrediction.objects.filter(user=user, prop_bet__game__in=completed, is_correct__isnull=False)
        correct, total = pp.filter(is_correct=True).count(), pp.count()
    return round(correct / total * 100, 1) if total > 0 else 0

def calculate_total_points_simple(user):
    """Simple total points calculation using completed games"""
    completed = Game.objects.filter(winner__isnull=False)
    cg = Prediction.objects.filter(user=user, game__in=completed, is_correct=True).count()
    cp = PropBetPrediction.objects.filter(user=user, prop_bet__game__in=completed, is_correct=True).count()
    return cg + (cp * 2)

def calculate_current_user_rank_realtime(user, current_week):
    """CRITICAL FIX: Use materialized view for performance, add live points"""
    _refresh_mv_if_needed()
    
    # Get base totals from materialized view
    try:
        user_totals = UserSeasonTotals.objects.get(user=user)
        base_points = user_totals.total_points
    except UserSeasonTotals.DoesNotExist:
        base_points = 0
    
    # Add current week live points
    live_points = calculate_live_stats(user, current_week)['weekly_points']
    user_total = base_points + live_points
    
    # Get all users with their totals
    rows = []
    for u in User.objects.all():
        try:
            u_totals = UserSeasonTotals.objects.get(user=u)
            u_base = u_totals.total_points
        except UserSeasonTotals.DoesNotExist:
            u_base = 0
        
        u_live = calculate_live_stats(u, current_week)['weekly_points']
        u_total = u_base + u_live
        rows.append({'user': u, 'username': u.username, 'total_points': u_total})
    
    assign_dense_ranks(rows, points_key='total_points')
    leader_points = rows[0]['total_points'] if rows else 0
    
    my_rank = None
    for r in rows:
        if r['user'] == user:
            my_rank = r['rank']
            break
    
    return {
        'rank': my_rank,
        'total_users': len(rows),
        'points_from_leader': leader_points - user_total,
    }

def get_best_category_realtime(user):
    """Determine user's best prediction category"""
    m = calculate_current_accuracy(user, 'moneyline')
    p = calculate_current_accuracy(user, 'prop')
    if m == 0 and p == 0:
        return "N/A", 0
    return ("Moneyline", m) if m >= p else ("Prop Bets", p)

def calculate_pending_picks(user, current_week):
    """Count pending predictions for current week"""
    games = Game.objects.filter(week=current_week).prefetch_related('prop_bets')
    made = set(Prediction.objects.filter(user=user, game__week=current_week).values_list('game_id', flat=True))
    pending_games = games.exclude(id__in=made).count()
    pending_props = 0
    for g in games:
        for pb in g.prop_bets.all():
            if not PropBetPrediction.objects.filter(user=user, prop_bet=pb).exists():
                pending_props += 1
    return pending_games + pending_props

def get_recent_games_data(user, limit=3):
    """Get recent completed games with user performance"""
    recents = Prediction.objects.filter(user=user, game__winner__isnull=False)\
        .select_related('game').order_by('-game__start_time')[:limit]
    out = []
    for p in recents:
        g = p.game
        out.append({
            'id': g.id,
            'homeTeam': g.home_team,
            'awayTeam': g.away_team,
            'userPick': p.predicted_winner,
            'result': g.winner,
            'correct': p.is_correct,
            'points': 1 if p.is_correct else 0,
        })
    return out

# ============================================================================
# RANK ACHIEVEMENTS (replacing arbitrary game streaks)
# ============================================================================

def get_user_rank_achievements(user):
    """Get rank-based achievements - much more meaningful than game streaks"""
    current_week = get_current_week()
    rank_history = UserStatHistory.objects.filter(user=user, week__lte=current_week).order_by('week')
    
    if not rank_history.exists():
        return {
            'current_rank': None,
            'consecutive_weeks_at_1': 0,
            'consecutive_weeks_in_top3': 0,
            'best_rank': None,
            'weeks_at_1': 0,
            'weeks_in_top3': 0,
            'biggest_climb': 0,
        }
    
    ranks = list(rank_history.values_list('rank', 'week'))
    current_rank = ranks[-1][0] if ranks else None
    best_rank = min(rank for rank, week in ranks)
    
    # Count consecutive weeks at #1 (current streak)
    consecutive_at_1 = 0
    for rank, week in reversed(ranks):
        if rank == 1:
            consecutive_at_1 += 1
        else:
            break
    
    # Count consecutive weeks in top 3 (current streak)
    consecutive_top3 = 0
    for rank, week in reversed(ranks):
        if rank <= 3:
            consecutive_top3 += 1
        else:
            break
    
    # Total achievements
    weeks_at_1 = sum(1 for rank, week in ranks if rank == 1)
    weeks_in_top3 = sum(1 for rank, week in ranks if rank <= 3)
    
    # Biggest single-week improvement
    biggest_climb = 0
    for i in range(1, len(ranks)):
        prev_rank = ranks[i-1][0]
        curr_rank = ranks[i][0]
        climb = prev_rank - curr_rank  # Positive = improved ranking
        if climb > biggest_climb:
            biggest_climb = climb
    
    return {
        'current_rank': current_rank,
        'consecutive_weeks_at_1': consecutive_at_1,
        'consecutive_weeks_in_top3': consecutive_top3,
        'best_rank': best_rank,
        'weeks_at_1': weeks_at_1,
        'weeks_in_top3': weeks_in_top3,
        'biggest_climb': biggest_climb,
        'total_weeks_tracked': len(ranks),
    }

# NOTE: This function references UserSeasonInsights model that may not exist yet
def get_user_season_stats(user):
    """Get season statistics - NOTE: May need UserSeasonInsights model"""
    # TODO: Verify if UserSeasonInsights model exists and is populated
    try:
        from ..models import UserSeasonInsights
        s = UserSeasonInsights.objects.get(user=user)
        return {
            'best_week_points': s.best_week_points,
            'best_week_number': s.best_week_number,
            'best_rank': s.best_rank,
            'weeks_in_top_3': s.weeks_in_top_3,
            'weeks_in_top_5': s.weeks_in_top_5,
            'weeks_at_rank_1': s.weeks_at_rank_1,
            'consecutive_weeks_at_1': s.consecutive_weeks_at_1,
            'biggest_rank_climb': s.biggest_rank_climb,
            'trending_direction': s.trending_direction,
        }
    except:
        return {
            'best_week_points': 0,
            'best_week_number': None,
            'best_rank': None,
            'weeks_in_top_3': 0,
            'weeks_in_top_5': 0,
            'weeks_at_rank_1': 0,
            'consecutive_weeks_at_1': 0,
            'biggest_rank_climb': 0,
            'trending_direction': 'stable',
        }

# ============================================================================
# LEADERBOARD FUNCTIONS
# ============================================================================

def get_leaderboard_data_realtime(limit=5):
    """Realtime leaderboard using materialized view + live points"""
    _refresh_mv_if_needed()
    current_week = get_current_week()
    rows = []
    
    for u in User.objects.all():
        # Get base points from materialized view
        try:
            totals = UserSeasonTotals.objects.get(user=u)
            base_points = totals.total_points
        except UserSeasonTotals.DoesNotExist:
            base_points = 0
        
        # Add live points
        live = calculate_live_stats(u, current_week)['weekly_points']
        total_points = base_points + live
        
        # Get trend info if available
        try:
            if TREND_UTILS_AVAILABLE:
                change_display, trend = get_user_rank_trend(u)
            else:
                change_display, trend = "—", "same"
        except:
            change_display, trend = "—", "same"
        
        rows.append({
            'username': u.username,
            'total_points': total_points,
            'trend': trend or 'same',
            'rank_change_display': change_display,
            'rank_change': 0,  # TODO: Calculate actual numeric change
        })
    
    assign_dense_ranks(rows, points_key='total_points')
    return rows[:limit] if limit else rows

# CRITICAL: Remove one of these duplicate functions - keeping the realtime version
# get_leaderboard_data_with_trends - REMOVED (was duplicate)

# ============================================================================
# ANALYTICS FUNCTIONS
# ============================================================================

def get_user_analytics_realtime(user):
    """Get user analytics based on rank achievements (not arbitrary game streaks)"""
    analytics = []
    
    # Get trend analytics if available
    if TREND_UTILS_AVAILABLE:
        try:
            analytics.extend(get_user_weekly_analytics(user))
        except Exception as e:
            print(f"Warning: weekly analytics error: {e}")
    
    # Rank-based achievements (much more meaningful)
    achievements = get_user_rank_achievements(user)
    
    if achievements['consecutive_weeks_at_1'] >= 2:
        weeks = achievements['consecutive_weeks_at_1']
        analytics.append({
            'type': 'positive', 
            'message': f"🏆 Dominant! You've been #1 for {weeks} consecutive weeks!"
        })
    elif achievements['consecutive_weeks_in_top3'] >= 3:
        weeks = achievements['consecutive_weeks_in_top3']
        analytics.append({
            'type': 'positive',
            'message': f"🔥 Consistent! Top 3 for {weeks} straight weeks!"
        })
    
    if achievements['biggest_climb'] >= 5:
        climb = achievements['biggest_climb']
        analytics.append({
            'type': 'achievement',
            'message': f"🚀 Epic comeback! Climbed {climb} spots in a single week!"
        })
    
    # Season achievements
    season = get_user_season_stats(user)
    if season['weeks_at_rank_1'] > 0:
        analytics.append({
            'type': 'positive', 
            'message': f"👑 You've led the league {season['weeks_at_rank_1']} time(s) this season!"
        })
    
    return analytics

# ============================================================================
# MAIN DASHBOARD FUNCTION (consolidated - removed duplicate)
# ============================================================================

def calculate_user_dashboard_data_realtime(user):
    """Main dashboard data calculation - REALTIME version"""
    current_week = get_current_week()
    live = calculate_live_stats(user, current_week)

    # Get trend data if available
    if TREND_UTILS_AVAILABLE:
        try:
            rank_delta_display, rank_trend = get_user_rank_trend(user)
            perf_trend = get_user_performance_trend(user)
            completed_total = sum(calculate_user_points_by_week(user).values())
        except Exception:
            rank_delta_display, rank_trend = "—", "same"
            perf_trend = "stable"
            completed_total = calculate_total_points_simple(user)
    else:
        rank_delta_display, rank_trend = "—", "same"
        perf_trend = "stable"
        completed_total = calculate_total_points_simple(user)

    rank_info = calculate_current_user_rank_realtime(user, current_week)
    total_points = completed_total + live['weekly_points']

    best_cat, best_acc = get_best_category_realtime(user)
    achievements = get_user_rank_achievements(user)
    season = get_user_season_stats(user)
    recent = get_recent_games_data(user, limit=3)

    return {
        'username': user.username,
        'currentWeek': current_week,
        'weeklyPoints': live['weekly_points'],
        'totalPoints': total_points,
        'rank': rank_info['rank'],
        'rankChange': rank_delta_display,
        'rankTrend': rank_trend,
        'totalUsers': rank_info['total_users'],
        'overallAccuracy': calculate_current_accuracy(user, 'overall'),
        'moneylineAccuracy': calculate_current_accuracy(user, 'moneyline'),
        'propBetAccuracy': calculate_current_accuracy(user, 'prop'),
        
        # Rank achievements (not arbitrary game streaks)
        'currentRank': achievements['current_rank'],
        'consecutiveWeeksAt1': achievements['consecutive_weeks_at_1'],
        'consecutiveWeeksInTop3': achievements['consecutive_weeks_in_top3'],
        'bestRank': achievements['best_rank'],
        'weeksAt1': achievements['weeks_at_1'],
        'biggestClimb': achievements['biggest_climb'],
        
        'pendingPicks': calculate_pending_picks(user, current_week),
        'pointsFromLeader': rank_info['points_from_leader'],
        'bestCategory': best_cat,
        'bestCategoryAccuracy': best_acc,
        'recentGames': recent,
        'seasonStats': season,
        'performanceTrend': perf_trend,
        'weeklyTrends': [],  # NOTE: Could add this back if needed
    }

# ============================================================================
# LEGACY/SNAPSHOT FUNCTIONS (marked for review)
# ============================================================================

# NOTE: These functions use WeeklySnapshot which is marked as deprecated
# TODO: Decide if these should be removed or updated to use UserStatHistory

def calculate_user_dashboard_data(user):
    """LEGACY: Snapshot-based dashboard - uses deprecated WeeklySnapshot"""
    # NOTE: This still uses WeeklySnapshot which is marked deprecated
    # TODO: Update to use UserStatHistory or remove entirely
    return calculate_user_dashboard_data_realtime(user)  # Fallback to realtime for now

def get_user_analytics(user):
    """LEGACY: Snapshot-based analytics"""
    # NOTE: Simplified to use realtime version for now
    return get_user_analytics_realtime(user)