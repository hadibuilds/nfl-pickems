# predictions/utils/dashboard_utils.py — snapshot-first, fast set-based reads
from __future__ import annotations
from typing import Dict, Tuple, List
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone
from django.db.models import Prefetch

from ..models import MoneyLinePrediction, PropBetPrediction, UserStatHistory
from games.models import Game, Window
from analytics.models import UserWindowStat  # snapshot table we write in window_stats


User = get_user_model()

# -------- week selection: earliest incomplete window -> its week; else next kickoff; else last week
def get_current_week(season: int | None = None) -> int:
    qs = Window.objects.filter(is_complete=False)
    if season is not None:
        qs = qs.filter(season=season)
    # order by PT spine (date, slot)
    w = (qs.extra(select={"_ord": "CASE slot WHEN 'morning' THEN 0 WHEN 'afternoon' THEN 1 ELSE 2 END"})
           .order_by("date", "_ord")
           .first())
    if w:
        wk = (Game.objects.filter(window=w)
                          .values_list("week", flat=True)
                          .order_by("week")
                          .first())
        if wk is not None:
            return int(wk)

    now = timezone.now()
    nxt = Game.objects.filter(start_time__gte=now)
    if season is not None:
        nxt = nxt.filter(season=season)
    wk = nxt.order_by("start_time").values_list("week", flat=True).first()
    if wk is not None:
        return int(wk)

    return int(Game.objects.order_by("-week").values_list("week", flat=True).first() or 1)


# -------- live weekly numbers (snapshot-first)
def calculate_live_stats(user, current_week: int) -> Dict[str, int]:
    win_ids = Game.objects.filter(week=current_week).values_list("window_id", flat=True).distinct()
    agg = (UserWindowStat.objects
           .filter(user=user, window_id__in=win_ids)
           .aggregate(points=Sum("season_cume_points"), ml=Sum("ml_correct"), pb=Sum("pb_correct")))
    weekly_points = int(agg["points"] or 0)
    game_correct  = int(agg["ml"] or 0)
    prop_correct  = int(agg["pb"] or 0)
    return {"weekly_points": weekly_points, "game_correct": game_correct, "prop_correct": prop_correct}


def calculate_current_user_rank_realtime(user, current_week: int) -> Dict[str, int | None]:
    win_ids = list(Game.objects.filter(week=current_week).values_list("window_id", flat=True).distinct())
    rows = list(
        UserWindowStat.objects
        .filter(window_id__in=win_ids)
        .values("user_id")
        .annotate(points=Sum("season_cume_points"))
        .order_by("-points", "user_id")
    )
    rank = 0; seen = 0; last_pts = None; leader = 0; my_rank = None; my_pts = 0
    for r in rows:
        pts = int(r["points"] or 0); seen += 1
        if last_pts is None or pts < last_pts:
            rank = seen; last_pts = pts
        if seen == 1:
            leader = pts
        if r["user_id"] == user.id:
            my_rank = rank; my_pts = pts
    return {"rank": my_rank, "total_users": len(rows), "points_from_leader": max(0, leader - my_pts)}


def calculate_pending_picks(user, current_week: int) -> int:
    now = timezone.now()
    unlocked_games = Game.objects.filter(week=current_week).exclude(Q(locked=True) | Q(start_time__lte=now))
    ml_pending = unlocked_games.exclude(
        id__in=MoneyLinePrediction.objects.filter(user=user).values("game_id")
    ).count()

    unlocked_prop_ids = (PropBetPrediction.objects
                         .filter(user=user, prop_bet__game__week=current_week)
                         .values_list("prop_bet_id", flat=True))  # already answered ids
    total_prop_ids = list(Game.objects.filter(week=current_week, id__in=unlocked_games.values("id"))
                                .values_list("prop_bets__id", flat=True))
    pb_pending = len([pid for pid in total_prop_ids if pid and pid not in set(unlocked_prop_ids)])
    return int(ml_pending + pb_pending)


# -------- accuracy
def calculate_current_accuracy(user, kind: str) -> int:
    def pct(c, t): return 0 if not t else int(round(100 * c / t))
    if kind == "moneyline":
        qs = MoneyLinePrediction.objects.filter(user=user, is_correct__isnull=False)
        return pct(qs.filter(is_correct=True).count(), qs.count())
    if kind == "prop":
        qs = PropBetPrediction.objects.filter(user=user, is_correct__isnull=False)
        return pct(qs.filter(is_correct=True).count(), qs.count())

    ml = MoneyLinePrediction.objects.filter(user=user, is_correct__isnull=False)
    pb = PropBetPrediction.objects.filter(user=user, is_correct__isnull=False)
    total = ml.count() + pb.count()
    correct = ml.filter(is_correct=True).count() + pb.filter(is_correct=True).count()
    return pct(correct, total)


def get_best_category_realtime(user) -> Tuple[str, int]:
    ml = calculate_current_accuracy(user, "moneyline")
    pb = calculate_current_accuracy(user, "prop")
    if ml == 0 and pb == 0:
        return "N/A", 0
    return ("Moneyline", ml) if ml >= pb else ("Prop Bets", pb)


# -------- one-call facade used by HomePage
def calculate_user_dashboard_data_realtime(user) -> Dict:
    wk = get_current_week()
    live = calculate_live_stats(user, wk)
    rank = calculate_current_user_rank_realtime(user, wk)
    pending = calculate_pending_picks(user, wk)
    best_cat, best_pct = get_best_category_realtime(user)
    return {
        "username": user.username,
        "currentWeek": wk,
        "weeklyPoints": live["weekly_points"],
        "rank": rank["rank"],
        "totalUsers": rank["total_users"],
        "pointsFromLeader": rank["points_from_leader"],
        "pendingPicks": pending,
        "bestCategory": best_cat,
        "bestCategoryAccuracy": best_pct,
    }

# --- season leaderboard (cumulative) ---

def _resolve_season(season: int | None) -> int | None:
    """
    Choose a season if none provided:
    - prefer the most recent season with Windows,
    - otherwise fall back to most recent season with Games.
    """
    if season is not None:
        return season
    s = (Window.objects.order_by('-season')
         .values_list('season', flat=True)
         .first())
    if s is None:
        s = (Game.objects.order_by('-season')
             .values_list('season', flat=True)
             .first())
    return int(s) if s is not None else None


def get_season_leaderboard(limit: int = 3, season: int | None = None):
    """
    Season leaderboard (TOP-N by cumulative points across ALL windows in the season).
    Returns: [{ user_id, username, window_points }] (field sourced from season_cume_points)
    """
    season_val = _resolve_season(season)
    if season_val is None:
        return []

    rows = (
        UserWindowStat.objects
        .filter(window__season=season_val)
        .values('user_id')
        .annotate(season_cume_points=Sum('season_cume_points')) 
        .order_by('-season_cume_points', 'user_id')[:limit]
    )

    # attach usernames
    uids = [r['user_id'] for r in rows]
    names = dict(User.objects.filter(id__in=uids).values_list('id', 'username'))

    return [
        {
            'user_id': r['user_id'],
            'username': names.get(r['user_id'], f'user-{r["user_id"]}'),
            'window_points': int(r['season_cume_points'] or 0),
        }
        for r in rows
    ]

def get_recent_games_data(user, limit: int = 3):
    """
    Return ALL recent games from completed windows, regardless of whether user made predictions.
    Missing picks are treated as incorrect (no points). Shows the facts!
    """
    # Get all games with resolved results (regardless of window completion)
    games = (
        Game.objects
        .filter(
            winner__isnull=False
        )
        .select_related('window')
        .prefetch_related('prop_bets')
        .order_by('-start_time')[:int(limit)]
    )
    
    if not games:
        return []
    
    # Get user's predictions for these games
    game_ids = [g.id for g in games]
    ml_predictions = {
        p.game_id: p for p in 
        MoneyLinePrediction.objects.filter(user=user, game_id__in=game_ids)
    }
    
    # Get prop bet predictions (need to check each game's prop bets)
    pb_predictions = {}
    all_prop_bet_ids = []
    for game in games:
        for pb in game.prop_bets.all():
            if pb.correct_answer:  # Only resolved prop bets
                all_prop_bet_ids.append(pb.id)
    
    if all_prop_bet_ids:
        for p in PropBetPrediction.objects.filter(user=user, prop_bet_id__in=all_prop_bet_ids):
            pb_predictions[p.prop_bet.game_id] = p
    
    results = []
    for game in games:
        # Check if game has a resolved prop bet
        resolved_prop_bet = None
        for pb in game.prop_bets.all():
            if pb.correct_answer:
                resolved_prop_bet = pb
                break
        
        # Get user's predictions (or None if missing)
        ml_pred = ml_predictions.get(game.id)
        pb_pred = pb_predictions.get(game.id) if resolved_prop_bet else None
        
        # Calculate ML correctness (missing = wrong)
        if ml_pred:
            ml_correct = ml_pred.is_correct
            ml_pick = ml_pred.predicted_winner
        else:
            ml_correct = False  # Missing pick = wrong
            ml_pick = "No Pick"
        
        # Calculate PB correctness (missing = wrong, or N/A if no prop bet exists)
        if resolved_prop_bet:
            if pb_pred:
                pb_correct = pb_pred.is_correct
                pb_pick = pb_pred.answer
            else:
                pb_correct = False  # Missing pick = wrong
                pb_pick = "No Pick"
        else:
            # No prop bet for this game
            pb_correct = None  # N/A
            pb_pick = "N/A"
        
        # Calculate points
        ml_points = 1 if ml_correct else 0
        pb_points = 2 if pb_correct else 0  # pb_correct can be None, which gives 0
        total_points = ml_points + pb_points
        
        # Color logic based on actual results
        if resolved_prop_bet:
            # Game has prop bet - use full 3-way logic
            correct_count = sum([ml_correct, pb_correct])
            if correct_count == 2:
                correct_status = 'full'    # Green - both correct
            elif correct_count == 1:
                correct_status = 'partial' # Yellow - one correct
            else:
                correct_status = 'none'    # Red - both wrong/missing
        else:
            # Game has no prop bet - just ML result
            if ml_correct:
                correct_status = 'full'    # Green - ML correct
            else:
                correct_status = 'none'    # Red - ML wrong/missing
        
        # Pick format: "ML, PB" or just "ML" if no prop bet
        if resolved_prop_bet:
            user_pick = f"{ml_pick}, {pb_pick}"
        else:
            user_pick = ml_pick
        
        results.append({
            'id': game.id,
            'awayTeam': game.away_team,
            'homeTeam': game.home_team,
            'points': total_points,
            'userPick': user_pick,
            'correct': correct_status == 'full',  # For backwards compatibility 
            'correctStatus': correct_status,  # New field for 3-way logic
        })
    
    return results

def get_user_insights_realtime(user, max_items: int = 6):
    """
    Returns a small set of human-friendly insights driven by LIVE analytics
    (UserWindowStat.season_cume_points) + current predictions accuracy.
    """
    # Current week & gap to leader
    wk = get_current_week()
    rank = calculate_current_user_rank_realtime(user, wk)

    # Totals across all windows (LIVE)
    totals = (
        UserWindowStat.objects
        .filter(user=user)
        .aggregate(
            points=Sum("season_cume_points"),
            ml=Sum("ml_correct"),
            pb=Sum("pb_correct"),
        )
    )
    season_points = int(totals["points"] or 0)
    ml_correct = int(totals["ml"] or 0)
    pb_correct = int(totals["pb"] or 0)

    # Best week (points)
    best_week = None
    best_pts = 0
    # map window -> week, then sum by week
    window_weeks = dict(
        Game.objects.values_list("window_id", "week").distinct()
    )
    rows = (
        UserWindowStat.objects
        .filter(user=user)
        .values("window_id")
        .annotate(points=Sum("season_cume_points"))
    )
    by_week = {}
    for r in rows:
        wknum = window_weeks.get(r["window_id"])
        if wknum is None:
            continue
        by_week[wknum] = by_week.get(wknum, 0) + int(r["points"] or 0)
    if by_week:
        best_week, best_pts = max(by_week.items(), key=lambda kv: kv[1])

    insights = []

    # Gap to leader (this week)
    if isinstance(rank.get("points_from_leader"), int):
        insights.append({
            "type": "gap_to_leader",
            "title": "Gap to Leader (This Week)",
            "value": rank["points_from_leader"],
            "meta": {"week": wk}
        })

    # Best category (accuracy)
    best_cat, best_pct = get_best_category_realtime(user)
    insights.append({
        "type": "best_category",
        "title": "Best Category",
        "value": best_cat,
        "meta": {"accuracyPercent": int(best_pct)}
    })

    # Season total points
    insights.append({
        "type": "season_points",
        "title": "Season Points",
        "value": season_points,
        "meta": {"ml_correct": ml_correct, "prop_correct": pb_correct}
    })

    # Best week
    if best_week is not None:
        insights.append({
            "type": "best_week",
            "title": f"Best Week",
            "value": best_pts,
            "meta": {"week": int(best_week)}
        })

    # Current week points (quick view)
    live = calculate_live_stats(user, wk)
    insights.append({
        "type": "this_week_points",
        "title": "This Week Points",
        "value": int(live.get("weekly_points", 0)),
        "meta": {"week": wk}
    })

    # Overall accuracy
    overall_acc = calculate_current_accuracy(user, "overall")
    insights.append({
        "type": "overall_accuracy",
        "title": "Overall Accuracy",
        "value": int(overall_acc),
        "meta": {"unit": "percent"}
    })

    return insights[:max_items]

def get_user_rank_achievements(user):
    """
    Returns simple achievement stats based on snapshot ranks (UserStatHistory).
    These are *historical* (require snapshots), not live.
    """
    qs = UserStatHistory.objects.filter(user=user).order_by("week")
    if not qs.exists():
        return {}

    weeks = list(qs)
    total_weeks = len(weeks)

    # best rank ever achieved
    best_rank = min([w.rank for w in weeks if w.rank is not None], default=None)

    # consecutive weeks at rank 1
    cons_1 = 0
    max_cons_1 = 0
    for w in weeks:
        if w.rank == 1:
            cons_1 += 1
            max_cons_1 = max(max_cons_1, cons_1)
        else:
            cons_1 = 0

    # consecutive weeks in top 3
    cons_top3 = 0
    max_cons_top3 = 0
    for w in weeks:
        if w.rank and w.rank <= 3:
            cons_top3 += 1
            max_cons_top3 = max(max_cons_top3, cons_top3)
        else:
            cons_top3 = 0

    # current rank (from latest snapshot)
    current_rank = weeks[-1].rank

    # total weeks at 1 / in top3
    weeks_at_1 = sum(1 for w in weeks if w.rank == 1)
    weeks_in_top3 = sum(1 for w in weeks if w.rank and w.rank <= 3)

    # biggest climb week-to-week
    biggest_climb = 0
    prev = None
    for w in weeks:
        if prev and prev.rank and w.rank:
            delta = prev.rank - w.rank
            biggest_climb = max(biggest_climb, delta)
        prev = w

    return {
        "current_rank": current_rank,
        "consecutive_weeks_at_1": max_cons_1,
        "consecutive_weeks_in_top_3": max_cons_top3,
        "best_rank": best_rank,
        "weeks_at_1": weeks_at_1,
        "weeks_in_top_3": weeks_in_top3,
        "biggest_climb": biggest_climb,
        "total_weeks_tracked": total_weeks,
    }


# If your views expect this older name, keep an alias:
get_leaderboard_data_realtime = get_season_leaderboard