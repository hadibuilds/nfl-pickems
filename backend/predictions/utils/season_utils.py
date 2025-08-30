# predictions/utils/season_utils.py
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Max, Sum

from ..models import MoneyLinePrediction, PropBetPrediction, UserStatHistory  # snapshots kept for ranks/accuracy history
from games.models import Game, PropBet                                         # PropBet is in games app
from analytics.models import UserWindowStat

from .dashboard_utils import get_leaderboard_data_realtime
from .ranking_utils import assign_dense_ranks as _assign

User = get_user_model()


# ------------------------------ helpers ------------------------------

def _window_ids_through_week(through_week: Optional[int]) -> List[int]:
    """Return distinct window_ids for games up to and including through_week.
    If through_week is None, returns all window_ids that exist on games."""
    qs = Game.objects.all()
    if through_week is not None:
        qs = qs.filter(week__lte=int(through_week))
    return list(qs.values_list("window_id", flat=True).distinct())


def _season_points_live(user: User, through_week: Optional[int] = None) -> int:
    """Sum of UserWindowStat.season_cume_points for the user (optionally <= through_week)."""
    win_ids = _window_ids_through_week(through_week)
    qs = UserWindowStat.objects.filter(user=user)
    if win_ids:
        qs = qs.filter(window_id__in=win_ids)
    return int(qs.aggregate(points=Sum("season_cume_points"))["points"] or 0)


def _week_points_live(user: User, week: int) -> int:
    """Sum of season_cume_points for a specific NFL week."""
    win_ids = list(
        Game.objects.filter(week=week).values_list("window_id", flat=True).distinct()
    )
    if not win_ids:
        return 0
    return int(
        UserWindowStat.objects.filter(user=user, window_id__in=win_ids)
        .aggregate(points=Sum("season_cume_points"))["points"]
        or 0
    )


# ------------------------------ rings / accuracy ------------------------------

def compute_user_season_rings(user: User, through_week: Optional[int] = None) -> Dict:
    """
    Accuracy denominators/numerators are still based on resolved games/props + user predictions.
    This is independent of season_cume_points and remains the right source of truth for accuracy.
    """
    games_qs = Game.objects.filter(winner__isnull=False)
    if through_week is not None:
        games_qs = games_qs.filter(week__lte=through_week)

    props_qs = PropBet.objects.filter(correct_answer__isnull=False, game__in=games_qs)

    ml_den = games_qs.count()
    prop_den = props_qs.count()

    correct_ml = MoneyLinePrediction.objects.filter(user=user, is_correct=True, game__in=games_qs).count()
    correct_prop = PropBetPrediction.objects.filter(user=user, is_correct=True, prop_bet__in=props_qs).count()

    def pct(n, d): return round((n / d) * 100, 1) if d > 0 else 0.0

    return {
        'ml_pct': pct(correct_ml, ml_den),
        'prop_pct': pct(correct_prop, prop_den),
        'overall_pct': pct(correct_ml + correct_prop, ml_den + prop_den),
        'den': {'ml': ml_den, 'prop': prop_den, 'overall': ml_den + prop_den},
        'num': {'ml': correct_ml, 'prop': correct_prop, 'overall': correct_ml + correct_prop},
        'games_qs': games_qs,
        'props_qs': props_qs,
    }


# ------------------------------ season stats (FAST, LIVE points) ------------------------------

def api_user_season_stats_fast(user: User, through_week: Optional[int] = None) -> Dict:
    """
    Returns current season numbers:
      - Points are LIVE (sum of UserWindowStat.season_cume_points), optionally limited to through_week.
      - Accuracy uses resolved games/props and user predictions (rings).
      - Trend/rank read from latest snapshot if present, but they don't affect points.
    """
    latest = UserStatHistory.objects.filter(user=user).order_by('-week').first()
    # rings use through_week if provided; else align to latest snapshot week (if exists)
    rings = compute_user_season_rings(user, through_week=through_week or (latest.week if latest else None))

    # rank trend from snapshots (optional)
    trend = 'same'
    if latest:
        prev = UserStatHistory.objects.filter(user=user, week__lt=latest.week).order_by('-week').first()
        if prev and latest.rank and prev.rank:
            delta = prev.rank - latest.rank
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

    # LIVE points from analytics
    season_points = _season_points_live(user, through_week=through_week)

    return {
        'current_season_points': season_points,
        'current_season_accuracy': rings['overall_pct'],
        'current_moneyline_accuracy': rings['ml_pct'],
        'current_prop_accuracy': rings['prop_pct'],
        'trending_direction': trend,
        'week': (through_week or (latest.week if latest else None)),
        'rank': (latest.rank if latest else None),
        'debug_counts': {
            'denominators': {
                'ml_games_completed': rings['den']['ml'],
                'props_resolved': rings['den']['prop'],
                'overall': rings['den']['overall']
            },
            'numerators': {
                'ml_correct': rings['num']['ml'],
                'prop_correct': rings['num']['prop'],
                'overall_correct': rings['num']['overall']
            },
        }
    }


# ------------------------------ window-based trends (NEW, from UserWindowStat) ------------------------------

def api_user_window_trends(user: User, windows_back: int = 2) -> Dict:
    """
    Get user's rank trend based on UserWindowStat window-to-window changes.
    Returns the last N windows to show rank progression.
    """
    from analytics.models import UserWindowStat
    from games.models import Window
    
    # Get recent completed windows in chronological order
    completed_windows = Window.objects.filter(
        is_complete=True
    ).order_by('-date', '-id')[:windows_back]
    
    if not completed_windows.exists():
        return {'trends': []}
    
    # Get user's stats for these windows
    window_ids = [w.id for w in completed_windows]
    user_stats = UserWindowStat.objects.filter(
        user=user, 
        window_id__in=window_ids
    ).select_related('window').order_by('window__date', 'window__id')
    
    trends = []
    prev_rank = None
    
    for stat in user_stats:
        rank_change = 0
        trend_dir = 'same'
        
        if prev_rank is not None:
            # Lower rank number = better (rank 1 > rank 2)
            rank_change = prev_rank - stat.rank_dense
            trend_dir = 'up' if rank_change > 0 else 'down' if rank_change < 0 else 'same'
        
        trends.append({
            'window_id': stat.window.id,
            'window_name': str(stat.window),
            'rank': stat.rank_dense,
            'rank_change': rank_change,
            'trend': trend_dir,
            'points': stat.season_cume_points
        })
        
        prev_rank = stat.rank_dense
    
    return {'trends': trends}


def build_season_leaderboard_with_window_trends(limit: int = 10) -> Dict:
    """
    Season leaderboard with rank trends based on window-to-window changes from UserWindowStat.
    """
    from analytics.models import UserWindowStat
    from games.models import Window
    
    # Get the two most recent completed windows
    recent_windows = Window.objects.filter(is_complete=True).order_by('-date', '-id')[:2]
    
    if recent_windows.count() < 1:
        # No completed windows yet, return current leaderboard without trends
        leaderboard = get_leaderboard_data_realtime(limit=limit)
        return {
            'standings': [{
                'username': r['username'],
                'total_points': r.get('window_points', 0),
                'rank_change': None,
                'trend': 'same'
            } for r in leaderboard]
        }
    
    current_window = recent_windows[0]
    prev_window = recent_windows[1] if recent_windows.count() >= 2 else None
    
    # Get current window stats
    current_stats = UserWindowStat.objects.filter(
        window=current_window
    ).select_related('user').order_by('-season_cume_points', 'user__username')[:limit]
    
    # Get previous window ranks if available
    prev_ranks = {}
    if prev_window:
        prev_stats = UserWindowStat.objects.filter(window=prev_window).values('user_id', 'rank_dense')
        prev_ranks = {stat['user_id']: stat['rank_dense'] for stat in prev_stats}
    
    standings = []
    for stat in current_stats:
        prev_rank = prev_ranks.get(stat.user.id)
        rank_change = None
        trend = 'same'
        
        if prev_rank is not None:
            rank_change = prev_rank - stat.rank_dense
            trend = 'up' if rank_change > 0 else 'down' if rank_change < 0 else 'same'
        
        standings.append({
            'username': stat.user.username,
            'total_points': stat.season_cume_points,
            'rank': stat.rank_dense,
            'rank_change': rank_change,
            'trend': trend
        })
    
    return {'standings': standings}


# ------------------------------ weekly trends (FAST, LIVE points) ------------------------------

def api_user_weekly_trends_fast(user: User, window: int = 5) -> Dict:
    """
    Emits a rolling window of weekly trend rows.
    - Points and total_points are LIVE from analytics (season_cume_points).
    - Rank and per-week accuracy fields are read from snapshots if available.
    """
    rows = list(UserStatHistory.objects.filter(user=user).order_by('week'))
    if not rows:
        return {'trends': []}

    rows = rows[-max(1, int(window)):]
    trends: List[Dict] = []
    prev = None

    for r in rows:
        wk = int(getattr(r, 'week', 0) or 0)

        # rank delta vs previous snapshot
        rank_change = 0
        trend_dir = 'same'
        if prev and getattr(r, 'rank', None) and getattr(prev, 'rank', None):
            delta = prev.rank - r.rank
            rank_change = delta
            trend_dir = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

        # LIVE points
        week_points = _week_points_live(user, wk)
        cumulative_points = _season_points_live(user, through_week=wk)

        trends.append({
            'week': wk,
            'points': week_points,
            'total_points': cumulative_points,
            'rank': getattr(r, 'rank', None),
            'rank_change': rank_change,
            'trend': trend_dir,
            'accuracy': getattr(r, 'season_accuracy', 0) or 0,
            'moneyline_accuracy': getattr(r, 'moneyline_accuracy', 0) or 0,
            'prop_accuracy': getattr(r, 'prop_accuracy', 0) or 0,
        })
        prev = r

    return {'trends': trends}


# ------------------------------ season leaderboard (FAST, LIVE points) ------------------------------

def _points_map_live_through_week(through_week: Optional[int] = None) -> Dict[str, int]:
    """
    Build {username -> total_points} using analytics (optionally <= through_week).
    """
    users = User.objects.all().only('id', 'username')
    pts_by_user: Dict[str, int] = {}
    win_ids = _window_ids_through_week(through_week)

    base_qs = UserWindowStat.objects.all()
    if win_ids:
        base_qs = base_qs.filter(window_id__in=win_ids)

    # Sum by user_id in one query
    rows = (
        base_qs.values('user_id')
        .annotate(points=Sum('season_cume_points'))
    )

    id_to_name = dict(users.values_list('id', 'username'))
    for r in rows:
        uname = id_to_name.get(r['user_id'])
        if not uname:
            continue
        pts_by_user[uname] = int(r['points'] or 0)

    # ensure users without rows appear with 0 (stable length for ranking)
    for u in users:
        pts_by_user.setdefault(u.username, 0)

    return pts_by_user


# ------------------------------ season leaderboard (DYNAMIC: realtime vs snapshot) ------------------------------

def build_season_leaderboard_dynamic(limit: int = 10) -> Dict:
    """
    Compares LIVE (analytics) ranks to baseline snapshot ranks to emit trend arrows.
    - LIVE side: get_leaderboard_data_realtime() returns rows with 'season_cume_points'
    - Baseline: latest snapshot rank per user, if available
    """
    # LIVE list for rank mapping
    realtime = get_leaderboard_data_realtime(limit=None)  # returns [{username, season_cume_points, ...}]
    current_rows = [{
        'username': r['username'],
        'total_points': r.get('window_points', r.get('total_points', r.get('points', 0))),
    } for r in realtime]
    _assign(current_rows, points_key='total_points')
    current_rank_map = {r['username']: r['rank'] for r in current_rows}

    # latest snapshot rank per user (baseline)
    baseline_rank = {}
    seen = set()
    # Using values() to de-dup quickly, then fetching the latest per user
    for row in UserStatHistory.objects.values('user__username').order_by('user__username', '-week'):
        uname = row['user__username']
        if uname in seen:
            continue
        latest = UserStatHistory.objects.filter(user__username=uname).order_by('-week').first()
        baseline_rank[uname] = getattr(latest, 'rank', None) if latest else None
        seen.add(uname)

    enriched = []
    for row in current_rows:
        uname = row['username']
        base = baseline_rank.get(uname)
        cur = current_rank_map.get(uname)
        if isinstance(base, int) and isinstance(cur, int):
            delta = base - cur
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'
        else:
            delta = 0
            trend = 'same'
        enriched.append({
            'username': uname,
            'total_points': row['total_points'],
            'rank': cur,
            'trend': trend,
            'rank_change': delta,
        })

    enriched.sort(key=lambda r: (-r['total_points'], r['username'].lower()))
    _assign(enriched, points_key='total_points')  # safety re-rank after sort
    lim = min(int(limit), 50)
    return {'standings': enriched[:lim], 'limit': lim, 'mode': 'realtime_vs_snapshot'}

def get_user_season_stats(user, season=None):
    qs = UserWindowStat.objects.filter(user=user)
    if season is not None:
        qs = qs.filter(window__season=season)
    return {
        "totalPoints": qs.aggregate(points=Sum("season_cume_points"))["points"] or 0
    }