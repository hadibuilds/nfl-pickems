# predictions/utils/dashboard_utils.py — updated without UserStreak, focus on rank-based insights
from django.contrib.auth import get_user_model
from ..models import (
    Prediction, PropBetPrediction, WeeklySnapshot,
    UserStatHistory, LeaderboardSnapshot, SeasonStats
)
from games.models import Game

User = get_user_model()

# ---- Helpers imported from trend_utils (with fallback) ----
try:
    from .trend_utils import (
        get_completed_weeks,
        calculate_user_points_by_week,
        calculate_user_rank_by_week,
        get_user_rank_trend,
        get_user_performance_trend,
        get_user_weekly_insights,
    )
    TREND_UTILS_AVAILABLE = True
except Exception as e:
    print(f"Warning importing trend_utils: {e}")
    TREND_UTILS_AVAILABLE = False


def get_current_week():
    """Return the first week that is not fully complete; if all done, return last week."""
    all_weeks = Game.objects.values_list('week', flat=True).distinct().order_by('week')
    for week in all_weeks:
        wg = Game.objects.filter(week=week)
        if wg.exists() and wg.filter(winner__isnull=False).count() < wg.count():
            return week
    return all_weeks.last() if all_weeks else 1


# ---------------- REALTIME DASHBOARD ----------------

def calculate_live_stats(user, current_week):
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
    completed = Game.objects.filter(winner__isnull=False)
    cg = Prediction.objects.filter(user=user, game__in=completed, is_correct=True).count()
    cp = PropBetPrediction.objects.filter(user=user, prop_bet__game__in=completed, is_correct=True).count()
    return cg + (cp * 2)


from .ranking_utils import assign_dense_ranks


def calculate_current_user_rank_realtime(user, current_week):
    """Realtime user rank using DENSE ranking (1,2,2,3)."""
    rows = []
    for u in User.objects.all():
        completed_total = sum(calculate_user_points_by_week(u).values()) if TREND_UTILS_AVAILABLE else calculate_total_points_simple(u)
        live = calculate_live_stats(u, current_week)['weekly_points']
        rows.append({'user': u, 'username': u.username, 'total_points': completed_total + live})
    assign_dense_ranks(rows, points_key='total_points')
    rows.sort(key=lambda r: (r['rank'], r['username']))  # deterministic
    leader_points = rows[0]['total_points'] if rows else 0
    me = next((r for r in rows if r['user'] == user), None)
    my_rank = me['rank'] if me else None
    my_points = me['total_points'] if me else 0
    return {
        'rank': my_rank,
        'total_users': len(rows),
        'points_from_leader': leader_points - my_points,
    }


def get_best_category_realtime(user):
    m = calculate_current_accuracy(user, 'moneyline')
    p = calculate_current_accuracy(user, 'prop')
    if m == 0 and p == 0:
        return "N/A", 0
    return ("Moneyline", m) if m >= p else ("Prop Bets", p)


def get_weekly_performance_trends_realtime(user, weeks=5):
    if not TREND_UTILS_AVAILABLE:
        return []
    completed = get_completed_weeks()
    recent = completed[-min(weeks, len(completed)):] if completed else []
    pts_by_week = calculate_user_points_by_week(user) if recent else {}

    trends = []
    for wk in recent:
        week_games = Game.objects.filter(week=wk, winner__isnull=False)
        gp = Prediction.objects.filter(user=user, game__in=week_games)
        pp = PropBetPrediction.objects.filter(user=user, prop_bet__game__in=week_games, is_correct__isnull=False)
        total = gp.count() + pp.count()
        correct = gp.filter(is_correct=True).count() + pp.filter(is_correct=True).count()
        acc = round(correct / total * 100, 1) if total > 0 else 0
        trends.append({
            'week': wk,
            'points': pts_by_week.get(wk, 0),
            'rank': calculate_user_rank_by_week(user, wk),
            'accuracy': acc,
            'rank_change': 0,
            'trend': 'same',
        })
    return sorted(trends, key=lambda x: x['week'])


def get_user_rank_achievements(user):
    """
    Get rank-based achievements instead of arbitrary game streaks.
    Much more meaningful than streak data.
    """
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
    
    # Count consecutive weeks at #1 (current)
    consecutive_at_1 = 0
    for rank, week in reversed(ranks):
        if rank == 1:
            consecutive_at_1 += 1
        else:
            break
    
    # Count consecutive weeks in top 3 (current)
    consecutive_top3 = 0
    for rank, week in reversed(ranks):
        if rank <= 3:
            consecutive_top3 += 1
        else:
            break
    
    # Total weeks at #1 and in top 3
    weeks_at_1 = sum(1 for rank, week in ranks if rank == 1)
    weeks_in_top3 = sum(1 for rank, week in ranks if rank <= 3)
    
    # Find biggest single-week climb
    biggest_climb = 0
    for i in range(1, len(ranks)):
        prev_rank = ranks[i-1][0]
        curr_rank = ranks[i][0]
        climb = prev_rank - curr_rank  # Positive = climbed up
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


def get_user_season_stats(user):
    try:
        s = SeasonStats.objects.get(user=user)
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
    except SeasonStats.DoesNotExist:
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


def get_recent_games_data(user, limit=3):
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


def get_user_insights_realtime(user):
    """Updated to use rank-based insights instead of game streaks."""
    insights = []
    
    if TREND_UTILS_AVAILABLE:
        try:
            insights.extend(get_user_weekly_insights(user))
        except Exception as e:
            print(f"weekly insights error: {e}")
    
    # Get rank-based achievements instead of streaks
    achievements = get_user_rank_achievements(user)
    
    # Rank-based insights (much better than game streaks)
    if achievements['consecutive_weeks_at_1'] >= 2:
        weeks = achievements['consecutive_weeks_at_1']
        insights.append({
            'type': 'positive', 
            'message': f"🏆 Dominant! You've been #1 for {weeks} consecutive weeks!"
        })
    elif achievements['consecutive_weeks_in_top3'] >= 3:
        weeks = achievements['consecutive_weeks_in_top3']
        insights.append({
            'type': 'positive',
            'message': f"🔥 Consistent! Top 3 for {weeks} straight weeks!"
        })
    
    if achievements['biggest_climb'] >= 5:
        climb = achievements['biggest_climb']
        insights.append({
            'type': 'achievement',
            'message': f"🚀 Epic comeback! Climbed {climb} spots in a single week!"
        })
    
    # Season-based insights
    season = get_user_season_stats(user)
    if season['weeks_at_rank_1'] > 0:
        insights.append({
            'type': 'positive', 
            'message': f"👑 You've led the league {season['weeks_at_rank_1']} time(s) this season!"
        })
    
    return insights


def calculate_user_dashboard_data_realtime(user):
    current_week = get_current_week()
    live = calculate_live_stats(user, current_week)

    if TREND_UTILS_AVAILABLE:
        try:
            rank_delta_display, rank_trend = get_user_rank_trend(user)
        except Exception:
            rank_delta_display, rank_trend = "—", "same"
        try:
            weekly_trends = get_weekly_performance_trends_realtime(user, weeks=5)
            perf_trend = get_user_performance_trend(user)
        except Exception:
            weekly_trends, perf_trend = [], "stable"
        completed_total = sum(calculate_user_points_by_week(user).values())
    else:
        rank_delta_display, rank_trend = "—", "same"
        weekly_trends, perf_trend = [], "stable"
        completed_total = calculate_total_points_simple(user)

    rank_info = calculate_current_user_rank_realtime(user, current_week)
    total_points = completed_total + live['weekly_points']

    best_cat, best_acc = get_best_category_realtime(user)
    achievements = get_user_rank_achievements(user)  # Rank achievements instead of streaks
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
        
        # Rank-based achievements instead of game streaks
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
        'weeklyTrends': weekly_trends,
    }


# ---------------- Legacy snapshot helpers (kept, but fixed) ----------------

def _current_total_points_snapshot_aware(user, current_week):
    """Compute live total using last snapshot as a baseline, if present."""
    latest = WeeklySnapshot.objects.filter(user=user, week__lt=current_week).order_by('-week').first()
    base = latest.total_points if latest else 0
    live = calculate_live_stats(user, current_week)['weekly_points']
    return base + live


def calculate_current_user_rank(user, current_week):
    """Legacy: rank using snapshots as base for others (kept for back-compat)."""
    scores = []
    for u in User.objects.all():
        scores.append((u, _current_total_points_snapshot_aware(u, current_week)))
    scores.sort(key=lambda t: (-t[1], t[0].username))
    leader = scores[0][1] if scores else 0
    my_rank, my_points = 1, 0
    for i, (u, pts) in enumerate(scores):
        if u == user:
            my_rank, my_points = i + 1, pts
            break
    return {
        'rank': my_rank,
        'total_users': len(scores),
        'points_from_leader': leader - my_points,
    }


def get_user_rank_trends(user, current_week):
    current = calculate_current_user_rank(user, current_week)
    recent = UserStatHistory.objects.filter(user=user).order_by('-week')[:2]  # Updated model name
    change, trend = "—", "same"
    if recent:
        change, trend = recent[0].rank_change_display, recent[0].trend_direction
    return {
        'current_rank': current['rank'],
        'rank_change_display': change,
        'trend_direction': trend,
        'total_users': current['total_users'],
        'points_from_leader': current['points_from_leader'],
    }


def calculate_performance_trend(user):
    snaps = WeeklySnapshot.objects.filter(user=user).order_by('-week')[:4]
    if len(snaps) < 2:
        return 'stable'
    ranks = [s.rank for s in snaps]
    improving = sum(1 for i in range(len(ranks)-1) if ranks[i] < ranks[i+1])
    declining = sum(1 for i in range(len(ranks)-1) if ranks[i] > ranks[i+1])
    if improving > declining:
        return 'up'
    if declining > improving:
        return 'down'
    return 'stable'


def get_weekly_performance_trends(user, weeks=5):
    snaps = WeeklySnapshot.objects.filter(user=user).order_by('-week')[:weeks]
    out = []
    for s in snaps:
        rh = UserStatHistory.objects.filter(user=user, week=s.week).first()  # Updated model name
        out.append({
            'week': s.week,
            'points': s.weekly_points,
            'rank': s.rank,
            'accuracy': s.weekly_accuracy or 0,
            'rank_change': rh.rank_change if rh else 0,
            'trend': rh.trend_direction if rh else 'same',
        })
    return sorted(out, key=lambda x: x['week'])


def get_best_category_with_history(user):
    latest = WeeklySnapshot.objects.filter(user=user).order_by('-week').first()
    if latest:
        m = latest.moneyline_accuracy or 0
        p = latest.prop_accuracy or 0
    else:
        m = calculate_current_accuracy(user, 'moneyline')
        p = calculate_current_accuracy(user, 'prop')
    if m == 0 and p == 0:
        return "N/A", 0
    return ("Moneyline", m) if m >= p else ("Prop Bets", p)



def get_leaderboard_data_realtime(limit=5):
    """Realtime leaderboard slice using DENSE ranks (1,2,2,3)."""
    current_week = get_current_week()
    rows = []
    for u in User.objects.all():
        completed_total = sum(calculate_user_points_by_week(u).values()) if TREND_UTILS_AVAILABLE else calculate_total_points_simple(u)
        live = calculate_live_stats(u, current_week)['weekly_points']
        try:
            change_display, trend = get_user_rank_trend(u) if TREND_UTILS_AVAILABLE else ("—", "same")
        except Exception:
            change_display, trend = "—", "same"
        # derive numeric rank_change (positive = up) from string like "+2"/"-1"/"—"
        try:
            change_num = int(str(change_display)) if str(change_display).replace('+','').replace('-','').isdigit() else 0
        except Exception:
            change_num = 0
        rows.append({
            'username': u.username,
            'total_points': completed_total + live,
            'trend': trend or 'same',
            'rank_change_display': change_display,
            'rank_change': change_num,
        })
    assign_dense_ranks(rows, points_key='total_points')
    # slice (None -> full list is fine)
    sliced = rows if limit is None else rows[:limit]
    out = []
    for r in sliced:
        r.update({'rank': r['rank'], 'current_rank': r['rank'], 'current_points': r['total_points']})
        out.append(r)
    return out


def get_leaderboard_data_with_trends(limit=5):
    """Legacy leaderboard using snapshot baseline, but with correct current_points."""
    current_week = get_current_week()
    latest_snapshot = LeaderboardSnapshot.objects.filter(week__lt=current_week).order_by('-week').first()
    if latest_snapshot:
        leaderboard = latest_snapshot.snapshot_data[:limit]
        for entry in leaderboard:
            user = User.objects.get(username=entry['username'])
            # recompute live total correctly
            current_points = _current_total_points_snapshot_aware(user, current_week)
            entry['current_points'] = current_points
            # update current rank relative to others in this limited slice
        # recompute ranks within the limited list
        leaderboard.sort(key=lambda e: (-e['current_points'], e['username']))
        for i, e in enumerate(leaderboard):
            e['current_rank'] = i + 1
        return leaderboard

    # fallback purely realtime
    return get_leaderboard_data_realtime(limit=limit)


def calculate_pending_picks(user, current_week):
    games = Game.objects.filter(week=current_week).prefetch_related('prop_bets')
    made = set(Prediction.objects.filter(user=user, game__week=current_week).values_list('game_id', flat=True))
    pending_games = games.exclude(id__in=made).count()
    pending_props = 0
    for g in games:
        for pb in g.prop_bets.all():
            if not PropBetPrediction.objects.filter(user=user, prop_bet=pb).exists():
                pending_props += 1
    return pending_games + pending_props


# Snapshot-based functions (updated for UserStatHistory)

def calculate_user_dashboard_data(user):
    """
    Snapshot-based dashboard calculation using UserStatHistory
    """
    current_week = get_current_week()
    
    # Get the most recent rank history for this user
    latest_stat = UserStatHistory.objects.filter(user=user).order_by('-week').first()
    
    if latest_stat:
        # Use snapshot-based data when available
        rank = latest_stat.rank
        rank_change = latest_stat.rank_change_display
        rank_trend = latest_stat.trend_direction
        total_points = latest_stat.total_points
        
        # Add current week's live points
        live = calculate_live_stats(user, current_week)
        total_points += live['weekly_points']
    else:
        # Fallback to realtime if no snapshots exist
        return calculate_user_dashboard_data_realtime(user)
    
    # Get other stats (these don't depend on snapshots)
    best_cat, best_acc = get_best_category_realtime(user)
    achievements = get_user_rank_achievements(user)  # Use rank achievements
    season = get_user_season_stats(user)
    recent = get_recent_games_data(user, limit=3)
    
    # Calculate total users from latest leaderboard snapshot
    latest_leaderboard = LeaderboardSnapshot.objects.order_by('-week').first()
    total_users = len(latest_leaderboard.snapshot_data) if latest_leaderboard else User.objects.count()
    
    return {
        'username': user.username,
        'currentWeek': current_week,
        'weeklyPoints': live['weekly_points'],
        'totalPoints': total_points,
        'rank': rank,
        'rankChange': rank_change,
        'rankTrend': rank_trend,
        'totalUsers': total_users,
        'overallAccuracy': calculate_current_accuracy(user, 'overall'),
        'moneylineAccuracy': calculate_current_accuracy(user, 'moneyline'),
        'propBetAccuracy': calculate_current_accuracy(user, 'prop'),
        
        # Rank achievements instead of streaks
        'currentRank': achievements['current_rank'],
        'consecutiveWeeksAt1': achievements['consecutive_weeks_at_1'],
        'consecutiveWeeksInTop3': achievements['consecutive_weeks_in_top3'],
        'bestRank': achievements['best_rank'],
        'weeksAt1': achievements['weeks_at_1'],
        'biggestClimb': achievements['biggest_climb'],
        
        'pendingPicks': calculate_pending_picks(user, current_week),
        'pointsFromLeader': 0,  # Calculate this if needed
        'bestCategory': best_cat,
        'bestCategoryAccuracy': best_acc,
        'recentGames': recent,
        'seasonStats': season,
        'performanceTrend': 'stable',  # Could enhance this with UserStatHistory
        'weeklyTrends': [],  # Could enhance this with UserStatHistory
    }


def get_user_insights(user):
    """
    Snapshot-based insights using UserStatHistory and rank achievements
    """
    insights = []
    
    # Get rank trend insights from UserStatHistory
    recent_ranks = UserStatHistory.objects.filter(user=user).order_by('-week')[:3]
    if len(recent_ranks) >= 2:
        if recent_ranks[0].rank < recent_ranks[1].rank:
            change = recent_ranks[1].rank - recent_ranks[0].rank
            insights.append({
                'type': 'positive', 
                'message': f"📈 You climbed {change} spots since last week!"
            })
        elif recent_ranks[0].rank > recent_ranks[1].rank:
            change = recent_ranks[0].rank - recent_ranks[1].rank
            insights.append({
                'type': 'warning',
                'message': f"📉 You dropped {change} spots since last week."
            })
    
    # Get rank-based achievements instead of streaks
    achievements = get_user_rank_achievements(user)
    
    if achievements['consecutive_weeks_at_1'] >= 2:
        weeks = achievements['consecutive_weeks_at_1']
        insights.append({
            'type': 'positive',
            'message': f"🏆 Dominant! {weeks} consecutive weeks at #1!"
        })
    elif achievements['consecutive_weeks_in_top3'] >= 3:
        weeks = achievements['consecutive_weeks_in_top3']
        insights.append({
            'type': 'positive',
            'message': f"🔥 Consistent! Top 3 for {weeks} straight weeks!"
        })
    
    # Add season insights
    season = get_user_season_stats(user)
    if season['weeks_at_rank_1'] > 0:
        insights.append({
            'type': 'positive', 
            'message': f"👑 You've led the league {season['weeks_at_rank_1']} time(s)!"
        })
    
    return insights