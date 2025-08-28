# analytics/utils/season_utils.py
from django.contrib.auth import get_user_model
from django.db.models import Max
from rest_framework.response import Response

from ..models import Prediction, PropBetPrediction, UserStatHistory
from games.models import Game, PropBet

from .dashboard_utils import (
    calculate_total_points_simple,
    get_leaderboard_data_realtime,
    get_current_week,
)
from .ranking_utils import assign_dense_ranks as _assign

User = get_user_model()

def compute_user_season_rings(user, through_week=None):
    games_qs = Game.objects.filter(winner__isnull=False)
    if through_week is not None:
        games_qs = games_qs.filter(week__lte=through_week)

    props_qs = PropBet.objects.filter(correct_answer__isnull=False, game__in=games_qs)

    ml_den = games_qs.count()
    prop_den = props_qs.count()

    correct_ml = Prediction.objects.filter(user=user, is_correct=True, game__in=games_qs).count()
    correct_prop = PropBetPrediction.objects.filter(user=user, is_correct=True, prop_bet__in=props_qs).count()

    def pct(n, d): return round((n / d) * 100, 1) if d > 0 else 0.0

    return {
        'ml_pct': pct(correct_ml, ml_den),
        'prop_pct': pct(correct_prop, prop_den),
        'overall_pct': pct(correct_ml + correct_prop, ml_den + prop_den),
        'den': {'ml': ml_den, 'prop': prop_den, 'overall': ml_den + prop_den},
        'num': {'ml': correct_ml, 'prop': correct_prop, 'overall': correct_ml + correct_prop},
        'games_qs': games_qs,  # occasionally useful for callers
        'props_qs': props_qs,
    }

def api_user_season_stats_fast(user, through_week=None):
    latest = UserStatHistory.objects.filter(user=user).order_by('-week').first()
    rings = compute_user_season_rings(user, through_week=through_week or (latest.week if latest else None))

    trend = 'same'
    if latest:
        prev = UserStatHistory.objects.filter(user=user, week__lt=latest.week).order_by('-week').first()
        if prev and latest.rank and prev.rank:
            delta = prev.rank - latest.rank
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

    season_points = latest.total_points if latest else 0
    if not season_points:
        # conservative fallback
        season_points = rings['num']['ml'] * 1 + rings['num']['prop'] * 2

    return {
        'current_season_points': season_points,
        'current_season_accuracy': rings['overall_pct'],
        'current_moneyline_accuracy': rings['ml_pct'],
        'current_prop_accuracy': rings['prop_pct'],
        'trending_direction': trend,
        'week': (through_week or (latest.week if latest else None)),
        'rank': (latest.rank if latest else None),
        'debug_counts': {
            'denominators': {'ml_games_completed': rings['den']['ml'], 'props_resolved': rings['den']['prop'], 'overall': rings['den']['overall']},
            'numerators': {'ml_correct': rings['num']['ml'], 'prop_correct': rings['num']['prop'], 'overall_correct': rings['num']['overall']},
        }
    }

def api_user_weekly_trends_fast(user, window=5):
    rows = list(UserStatHistory.objects.filter(user=user).order_by('week'))
    if not rows:
        return {'trends': []}
    rows = rows[-max(1, int(window)):]

    trends = []
    prev = None
    for r in rows:
        rank_change = 0
        trend = 'same'
        if prev and getattr(r, 'rank', None) and getattr(prev, 'rank', None):
            delta = prev.rank - r.rank
            rank_change = delta
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'

        trends.append({
            'week': getattr(r, 'week', None),
            'points': getattr(r, 'weekly_points', None),
            'total_points': getattr(r, 'total_points', 0) or 0,
            'rank': getattr(r, 'rank', None),
            'rank_change': rank_change,
            'trend': trend,
            'accuracy': getattr(r, 'season_accuracy', 0) or 0,
            'moneyline_accuracy': getattr(r, 'moneyline_accuracy', 0) or 0,
            'prop_accuracy': getattr(r, 'prop_accuracy', 0) or 0,
        })
        prev = r
    return {'trends': trends}

def build_season_leaderboard_fast(through_week=None, limit=10):
    users = User.objects.all()
    board = []
    for u in users:
        qs = UserStatHistory.objects.filter(user=u)
        if through_week is not None:
            qs = qs.filter(week__lte=through_week)
        latest = qs.order_by('-week').first()
        total_pts = getattr(latest, 'total_points', 0) or 0 if latest else calculate_total_points_simple(u)
        board.append({'username': u.username, 'total_points': total_pts})

    _assign(board, points_key='total_points')

    if through_week is not None:
        prev_week = through_week - 1
    else:
        latest_week = UserStatHistory.objects.aggregate(m=Max('week'))['m']
        prev_week = latest_week - 1 if latest_week not in (None, 0) else None

    prev_rank_map = {}
    if prev_week and prev_week > 0:
        prev_rows = [
            {'username': s.user.username, 'total_points': getattr(s, 'total_points', 0) or 0}
            for s in UserStatHistory.objects.filter(week=prev_week)
        ]
        if prev_rows:
            _assign(prev_rows, points_key='total_points')
            prev_rank_map = {r['username']: r['rank'] for r in prev_rows}

    for r in board:
        old = prev_rank_map.get(r['username'])
        new_rank = r.get('rank')
        if isinstance(old, int) and isinstance(new_rank, int):
            delta = old - new_rank
            r['rank_change'] = delta
            r['trend'] = 'up' if delta > 0 else 'down' if delta < 0 else 'same'
        else:
            r['rank_change'] = 0
            r['trend'] = 'same'

    board.sort(key=lambda x: (-x.get('total_points', 0), x['username'].lower()))
    return {'standings': board[:min(int(limit), 50)], 'limit': min(int(limit), 50), 'through_week': through_week}

# at top of file (already imported): from .ranking_utils import assign_dense_ranks as _assign


def build_season_leaderboard_dynamic(limit=10):
    # full realtime list for rank mapping
    realtime = get_leaderboard_data_realtime(limit=None)
    # Normalize points key and compute dense ranks on the full list
    current_rows = [{
        'username': r['username'],
        'total_points': r.get('total_points', r.get('points', 0)),
    } for r in realtime]
    _assign(current_rows, points_key='total_points')
    current_rank_map = {r['username']: r['rank'] for r in current_rows}

    # latest snapshot rank per user
    baseline_rank = {}
    seen = set()
    for row in UserStatHistory.objects.values('user__username').order_by('user__username', '-week'):
        uname = row['user__username']
        if uname in seen:
            continue
        latest = UserStatHistory.objects.filter(user__username=uname).order_by('-week').first()
        baseline_rank[uname] = getattr(latest, 'rank', None) if latest else None
        seen.add(uname)

    enriched = []
    for row in current_rows:
        base = baseline_rank.get(row['username'])
        cur = current_rank_map.get(row['username'])
        if isinstance(base, int) and isinstance(cur, int):
            delta = base - cur
            trend = 'up' if delta > 0 else 'down' if delta < 0 else 'same'
        else:
            delta = 0
            trend = 'same'
        enriched.append({
            'username': row['username'],
            'total_points': row['total_points'],
            'rank': cur,
            'trend': trend,
            'rank_change': delta,
        })

    enriched.sort(key=lambda r: (-r['total_points'], r['username'].lower()))
    # dense rank within the final sorted list too (for safety)
    _assign(enriched, points_key='total_points')
    return {'standings': enriched[:min(int(limit), 50)], 'limit': min(int(limit), 50), 'mode': 'realtime_vs_snapshot'}

