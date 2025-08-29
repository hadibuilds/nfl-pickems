# predictions/utils/dashboard_utils.py — lean, set-based, snapshot-first
from __future__ import annotations

from typing import Dict, Tuple, List, Optional
from django.contrib.auth import get_user_model
from django.db.models import (
    Q, Count, Sum, Max, Min, F, IntegerField, Case, When, Value
)
from django.utils import timezone

# Domain models
from games.models import Game  # always present
try:
    from games.models import PropBet, Window
except Exception:  # legacy
    PropBet = None
    Window = None

try:
    # snapshots for super fast reads
    from analytics.models import UserWindowStat
except Exception:
    UserWindowStat = None

# Prediction models (moneyline/prop)
try:
    # new name
    from predictions.models import MoneyLinePrediction, PropBetPrediction
except Exception:
    # legacy names
    from .models import Prediction as MoneyLinePrediction  # type: ignore
    from .models import PropBetPrediction  # type: ignore

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Week resolution
# ──────────────────────────────────────────────────────────────────────────────

def get_current_week() -> int:
    """
    App definition: the *earliest week that has an incomplete window*.
    Falls back to the earliest week that has any ungraded game/prop,
    else the latest week in the dataset.
    """
    # Preferred: compute by Windows (earliest incomplete window → its games' week)
    if Window is not None:
        try:
            slot_order = Case(
                When(slot='morning', then=Value(0)),
                When(slot='afternoon', then=Value(1)),
                When(slot='late', then=Value(2)),
                default=Value(99),
                output_field=IntegerField(),
            )
            w = (
                Window.objects
                .filter(is_complete=False)
                .order_by('date', slot_order)
                .only('id')
                .first()
            )
            if w:
                wk = (
                    Game.objects
                    .filter(window_id=w.id)
                    .values_list('week', flat=True)
                    .order_by('week')
                    .first()
                )
                if wk is not None:
                    return int(wk)
        except Exception:
            pass

    # Fallback: earliest week that still has ungraded truth (games)
    week = (
        Game.objects
        .filter(Q(winner__isnull=True))
        .values_list('week', flat=True)
        .order_by('week')
        .first()
    )
    if week is not None:
        return int(week)

    # If everything is graded, return the latest week in the data set.
    last = Game.objects.values_list('week', flat=True).order_by('-week').first()
    return int(last or 1)


# ──────────────────────────────────────────────────────────────────────────────
# Live numbers (computed with set operations; no Python loops)
# ──────────────────────────────────────────────────────────────────────────────

def _week_window_ids(week: int) -> List[int]:
    if Window is None:
        return []
    return list(
        Game.objects.filter(week=week).values_list('window_id', flat=True).distinct()
    )


def calculate_live_stats(user, current_week: int) -> Dict[str, int]:
    """
    Live weekly points for a single user (ML=+1, Prop=+2), using graded truth only.
    Uses snapshots when available, else falls back to direct counts.
    """
    uid = getattr(user, 'id', user)
    if UserWindowStat is not None and Window is not None:
        win_ids = _week_window_ids(current_week)
        agg = (
            UserWindowStat.objects
            .filter(user_id=uid, window_id__in=win_ids)
            .aggregate(points=Sum('total_points'), ml=Sum('ml_correct'), pb=Sum('pb_correct'))
        )
        return {
            'weekly_points': int(agg['points'] or 0),
            'game_correct': int(agg['ml'] or 0),
            'prop_correct': int(agg['pb'] or 0),
        }

    # Fallback: count graded picks directly
    completed_games = Game.objects.filter(week=current_week, winner__isnull=False)
    game_correct = MoneyLinePrediction.objects.filter(
        user_id=uid, game__in=completed_games, is_correct=True
    ).count()
    prop_correct = PropBetPrediction.objects.filter(
        user_id=uid, prop_bet__game__in=completed_games, is_correct=True
    ).count()
    return {
        'weekly_points': int(game_correct + prop_correct * 2),
        'game_correct': int(game_correct),
        'prop_correct': int(prop_correct),
    }


def calculate_current_user_rank_realtime(user, current_week: int) -> Dict[str, Optional[int]]:
    """
    Dense rank for this user across the week (sum of all windows in the week).
    Uses UserWindowStat sums when available. Single query + O(n) pass in memory.
    """
    if UserWindowStat is not None and Window is not None:
        win_ids = _week_window_ids(current_week)
        weekly = (
            UserWindowStat.objects
            .filter(window_id__in=win_ids)
            .values('user_id')
            .annotate(points=Sum('total_points'))
            .order_by('-points', 'user_id')
        )
        # Compute dense rank (1,2,2,3) in one pass
        rank = 0
        seen = 0
        last_pts = None
        leader_points = 0
        my_rank = None
        my_points = 0
        uid = user.id
        as_list = list(weekly)
        for row in as_list:
            pts = int(row['points'] or 0)
            seen += 1
            if last_pts is None or pts < last_pts:
                rank = seen
                last_pts = pts
            if seen == 1:
                leader_points = pts
            if row['user_id'] == uid:
                my_rank = rank
                my_points = pts
        return {
            'rank': my_rank,
            'total_users': len(as_list),
            'points_from_leader': int(max(0, leader_points - my_points)),
        }

    # Fallback: minimal info without snapshots
    live = calculate_live_stats(user, current_week)['weekly_points']
    return {'rank': None, 'total_users': User.objects.count(), 'points_from_leader': 0}


def calculate_pending_picks(user, current_week: int) -> int:
    """
    Pending = unlocked & unanswered (moneyline + prop).
    Unlocked = not locked and start_time > now(), or explicit 'locked'=False.
    """
    now = timezone.now()
    # Games still open to pick
    unlocked_games = Game.objects.filter(
        week=current_week
    ).exclude(Q(locked=True) | Q(start_time__lte=now))

    # Moneyline pending
    my_ml = MoneyLinePrediction.objects.filter(user=user, game__week=current_week)\
                                       .values_list('game_id', flat=True)
    pending_games = unlocked_games.exclude(id__in=my_ml).count()

    # Props pending (for unlocked games only)
    if PropBet is None:
        pending_props = 0
    else:
        unlocked_prop_ids = PropBet.objects.filter(game__in=unlocked_games)\
                                           .values_list('id', flat=True)
        my_prop_ids = PropBetPrediction.objects.filter(
            user=user, prop_bet_id__in=unlocked_prop_ids
        ).values_list('prop_bet_id', flat=True)
        pending_props = PropBet.objects.filter(id__in=unlocked_prop_ids)\
                                       .exclude(id__in=my_prop_ids).count()

    return int(pending_games + pending_props)


# ──────────────────────────────────────────────────────────────────────────────
# Accuracy + best category (set-based aggregates)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_current_accuracy(user, kind: str) -> int:
    """
    Returns an integer percentage (0..100) for 'overall' | 'moneyline' | 'prop'.
    """
    uid = getattr(user, 'id', user)
    if kind == 'moneyline':
        qs = MoneyLinePrediction.objects.filter(user_id=uid, is_correct__isnull=False)
        total = qs.count()
        correct = qs.filter(is_correct=True).count()
    elif kind == 'prop':
        qs = PropBetPrediction.objects.filter(user_id=uid, is_correct__isnull=False)
        total = qs.count()
        correct = qs.filter(is_correct=True).count()
    else:
        ml = MoneyLinePrediction.objects.filter(user_id=uid, is_correct__isnull=False)
        pb = PropBetPrediction.objects.filter(user_id=uid, is_correct__isnull=False)
        total = ml.count() + pb.count()
        correct = ml.filter(is_correct=True).count() + pb.filter(is_correct=True).count()
    if total == 0:
        return 0
    return int(round((correct / total) * 100))


def get_best_category_realtime(user) -> Tuple[str, int]:
    m = calculate_current_accuracy(user, 'moneyline')
    p = calculate_current_accuracy(user, 'prop')
    if m == 0 and p == 0:
        return "N/A", 0
    return ("Moneyline", m) if m >= p else ("Prop Bets", p)


# ──────────────────────────────────────────────────────────────────────────────
# Recent games
# ──────────────────────────────────────────────────────────────────────────────

def get_recent_games_data(user, limit: int = 3) -> List[Dict]:
    """
    Last N completed picks across games/props with truth (fast + indexed).
    """
    ml = list(
        MoneyLinePrediction.objects
        .filter(user=user, is_correct__isnull=False)
        .select_related('game')
        .order_by('-game__start_time')
        .values('game_id', 'game__home_team', 'game__away_team', 'is_correct')[:limit*2]
    )
    pb = list()
    if PropBetPrediction is not None:
        pb = list(
            PropBetPrediction.objects
            .filter(user=user, is_correct__isnull=False)
            .select_related('prop_bet__game')
            .order_by('-prop_bet__game__start_time')
            .values('prop_bet_id', 'prop_bet__question', 'prop_bet__game__home_team',
                    'prop_bet__game__away_team', 'is_correct')[:limit*2]
        )
    items = []
    for r in ml[:limit]:
        items.append({
            'type': 'moneyline',
            'awayTeam': r['game__away_team'],
            'homeTeam': r['game__home_team'],
            'correct': bool(r['is_correct']),
            'points': 1 if r['is_correct'] else 0,
        })
    for r in pb[:limit]:
        items.append({
            'type': 'prop',
            'awayTeam': r['prop_bet__game__away_team'],
            'homeTeam': r['prop_bet__game__home_team'],
            'correct': bool(r['is_correct']),
            'points': 2 if r['is_correct'] else 0,
        })
    return items[:limit]


# ──────────────────────────────────────────────────────────────────────────────
# Leaderboard (realtime = sum per user across season)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_total_points_simple(user) -> int:
    """
    Season-to-date points – snapshot first (fast), else sum predictions.
    """
    uid = getattr(user, 'id', user)
    if UserWindowStat is not None:
        agg = UserWindowStat.objects.filter(user_id=uid).aggregate(points=Sum('total_points'))
        return int(agg['points'] or 0)
    ml = MoneyLinePrediction.objects.filter(user_id=uid, is_correct=True).count()
    pb = PropBetPrediction.objects.filter(user_id=uid, is_correct=True).count()
    return int(ml + pb * 2)


def get_leaderboard_data_realtime(limit: int = 10) -> List[Dict]:
    """
    Live season leaderboard (points), snapshot-backed.
    """
    if UserWindowStat is not None:
        sums = (
            UserWindowStat.objects.values('user_id')
            .annotate(total_points=Sum('total_points'))
            .order_by('-total_points', 'user_id')[:limit]
        )
        names = dict(User.objects.filter(id__in=[r['user_id'] for r in sums]).values_list('id', 'username'))
        return [
            {'user_id': r['user_id'], 'username': names.get(r['user_id'], f'user-{r["user_id"]}'),
             'total_points': int(r['total_points'] or 0)}
            for r in sums
        ]
    # Fallback: slower but still set-based
    ids = list(User.objects.values_list('id', flat=True))
    rows = []
    for uid in ids:
        rows.append({'user_id': uid, 'username': User.objects.get(id=uid).username,
                     'total_points': calculate_total_points_simple(uid)})
    rows.sort(key=lambda r: (-r['total_points'], r['user_id']))
    return rows[:limit]


# ──────────────────────────────────────────────────────────────────────────────
# Insights / achievements – kept light & read-only
# ──────────────────────────────────────────────────────────────────────────────

def get_user_rank_achievements(user) -> Dict[str, int]:
    """
    Placeholder: count of times rank==1 in snapshots.
    """
    if UserWindowStat is None:
        return {'consecutive_weeks_in_top3': 0, 'weeks_at_rank_1': 0}
    top3 = UserWindowStat.objects.filter(user=user, rank_dense__lte=3).count()
    tops = UserWindowStat.objects.filter(user=user, rank_dense=1).count()
    return {'consecutive_weeks_in_top3': top3, 'weeks_at_rank_1': tops}


def get_user_season_stats(user) -> Dict[str, int]:
    """
    Minimal season snapshot; keep for legacy callers.
    """
    return get_user_rank_achievements(user)


def get_user_insights_realtime(user) -> List[Dict]:
    ach = get_user_rank_achievements(user)
    insights: List[Dict] = []
    if ach.get('consecutive_weeks_in_top3'):
        insights.append({'type': 'positive', 'message': f"🔥 Consistent! Top 3 for {ach['consecutive_weeks_in_top3']} weeks."})
    if ach.get('weeks_at_rank_1'):
        insights.append({'type': 'positive', 'message': f"👑 Led the league {ach['weeks_at_rank_1']} time(s)."})
    return insights


# ──────────────────────────────────────────────────────────────────────────────
# One-call facade for the Home dashboard (kept for backwards-compat)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_user_dashboard_data_realtime(user) -> Dict:
    wk = get_current_week()
    live = calculate_live_stats(user, wk)
    rank = calculate_current_user_rank_realtime(user, wk)
    pending = calculate_pending_picks(user, wk)
    best_cat, best_pct = get_best_category_realtime(user)
    return {
        'username': user.username,
        'currentWeek': wk,
        'weeklyPoints': live['weekly_points'],
        'rank': rank['rank'],
        'totalUsers': rank['total_users'],
        'pointsFromLeader': rank['points_from_leader'],
        'pendingPicks': pending,
        'bestCategory': best_cat,
        'bestCategoryAccuracy': best_pct,
    }
