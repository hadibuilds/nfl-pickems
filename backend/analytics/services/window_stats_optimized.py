# analytics/services/window_stats_optimized.py
# OPTIMIZED window stats calculation - with security/safety hardening
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from games.models import Game, Window, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat

logger = logging.getLogger(__name__)

# --------------------------- scoring & behavior ----------------------------
def get_moneyline_points(week: int) -> int:
    """
    Return moneyline points based on week number.
    Weeks before MONEYLINE_POINTS_INCREASE_WEEK: 1 point
    Week MONEYLINE_POINTS_INCREASE_WEEK and after: 2 points
    """
    cutoff_week = getattr(settings, 'MONEYLINE_POINTS_INCREASE_WEEK', 9)
    return 2 if week >= cutoff_week else 1

PB_POINTS = 2   # points per correct prop-bet prediction

# Slot ordering for same-date windows (used for chronological sort stability)
SLOT_ORDER = {"morning": 0, "afternoon": 1, "late": 2}

# Recompute rate-limiting and mutex
RECOMPUTE_THROTTLE_SECONDS = getattr(settings, "WINDOW_RECOMPUTE_THROTTLE_SECONDS", 5)
RECOMPUTE_MUTEX_TTL = getattr(settings, "WINDOW_RECOMPUTE_MUTEX_TTL", 120)

# Optional roster scoping: restrict leaderboards to users in a given Django group name
# Set ANALYTICS_ROSTER_GROUP="my-league" in settings to enable. If unset, all active users are included.
ROSTER_GROUP = getattr(settings, "ANALYTICS_ROSTER_GROUP", None)


# ----------------------------- Data structures -----------------------------

@dataclass
class WindowInfo:
    id: int
    season: int
    date: str
    slot: str
    chronological_index: int

@dataclass
class UserDelta:
    user_id: int
    old_cume: int
    new_cume: int
    delta: int


# ------------------------------ Exceptions ---------------------------------

class WindowCalculationError(Exception):
    """Raised when window calculation fails or is not allowed."""
    pass


# ------------------------------- Guards ------------------------------------

def _assert_permission(actor) -> None:
    """
    Optional permission check for admin/API callers.
    - If actor is None -> treat as internal system call (signals/management commands).
    - Else require staff OR change permission on UserWindowStat.
    """
    if actor is None:
        return
    try:
        if actor.is_superuser or actor.is_staff:
            return
        if actor.has_perm("analytics.change_userwindowstat"):
            return
    except Exception:
        # Fallback to staff/superuser only if the auth backend doesn't support perms cleanly
        pass
    raise WindowCalculationError("Not authorized to recompute window stats.")


def _acquire_mutex(window_id: int) -> str:
    """
    Acquire a cache-based mutex so only one recompute runs per window at a time.
    Returns the lock key if acquired; raises if another worker holds it.
    """
    lock_key = f"lock:analytics:recompute_window:{window_id}"
    if not cache.add(lock_key, "1", timeout=RECOMPUTE_MUTEX_TTL):
        raise WindowCalculationError("A recompute for this window is already in progress.")
    return lock_key


def _release_mutex(lock_key: str) -> None:
    try:
        cache.delete(lock_key)
    except Exception:
        # Non-fatal
        pass


def _throttle_should_skip(window_id: int) -> bool:
    """
    Return True if we should skip this recompute due to recent activity.
    Never raises; acts as a soft debounce.
    """
    if RECOMPUTE_THROTTLE_SECONDS <= 0:
        return False
    k = f"throttle:analytics:recompute_window:{window_id}"
    if cache.get(k):
        return True
    cache.set(k, 1, RECOMPUTE_THROTTLE_SECONDS)
    return False


# ---------------------------- Roster utilities -----------------------------

def _get_roster_user_ids() -> Set[int]:
    """
    Resolve the roster of users who must appear in every window's leaderboard,
    even if they made no predictions (no-pick => zero points).
    By default: all active users. If ANALYTICS_ROSTER_GROUP is set, restrict to that group.
    """
    User = get_user_model()
    qs = User.objects.filter(is_active=True)
    if ROSTER_GROUP:
        qs = qs.filter(groups__name=ROSTER_GROUP)
    return set(qs.values_list("id", flat=True))


# -------------------------- Core calculator class --------------------------

class OptimizedWindowCalculator:
    """
    Optimized window calculator that eliminates over-calculation and improves performance.
    Security/safety additions:
      - Optional permission enforcement (via actor)
      - Per-window mutex & throttle
      - Defensive validation and tighter completeness flip
    """

    def __init__(self, window_id: int, *, actor=None):
        if not isinstance(window_id, int) or window_id <= 0:
            raise WindowCalculationError("Invalid window_id.")
        self.window_id = window_id
        self.actor = actor
        self.season_windows_cache: Optional[List[WindowInfo]] = None
        self.current_window: Optional[WindowInfo] = None
        self._mutex_key: Optional[str] = None

    @transaction.atomic
    def recompute_window(self) -> None:
        """
        Optimized, safe recomputation with validation, locking, throttling, and ranking.
        """
        # 0) Authorization (if actor provided)
        _assert_permission(self.actor)

        # 1) Throttle (de-bounce bursts)
        if _throttle_should_skip(self.window_id):
            logger.info("Recompute for window %s skipped by throttle.", self.window_id)
            return

        # 2) Mutex (expensive operation guard)
        self._mutex_key = _acquire_mutex(self.window_id)

        try:
            # 3) Validate and cache chronology
            self._validate_and_setup()

            # 4) Calculate per-user deltas for the full roster (no-pick => zero points)
            user_deltas = self._calculate_user_deltas()

            # 5) Upsert current window stats (writes ml_correct/pb_correct/window_points & cume)
            self._update_current_window_stats(user_deltas)

            # 6) Propagate cumulative deltas forward
            if user_deltas:
                self._propagate_deltas_forward(user_deltas)

            # 7) Recompute dense ranks and rank deltas
            self._update_rankings()

            # 8) Update completion status (with row lock)
            self._update_window_completeness()

            logger.info("Recomputed window %s: %d user changes", self.window_id, len(user_deltas))
        except Exception as e:
            logger.error("Failed to recompute window %s: %s", self.window_id, str(e))
            raise
        finally:
            if self._mutex_key:
                _release_mutex(self._mutex_key)

    # ---------- internals ----------

    def _validate_and_setup(self) -> None:
        """Validate window exists and cache chronological info."""
        try:
            window = Window.objects.only("id", "season", "date", "slot").get(pk=self.window_id)
        except Window.DoesNotExist:
            raise WindowCalculationError(f"Window {self.window_id} does not exist")

        # Chronology for the whole season (cached)
        self.season_windows_cache = self._get_chronological_windows(window.season)

        # Locate current window
        for w in self.season_windows_cache:
            if w.id == self.window_id:
                self.current_window = w
                break
        if not self.current_window:
            raise WindowCalculationError(f"Window {self.window_id} not found in season {window.season}")

    def _get_chronological_windows(self, season: int) -> List[WindowInfo]:
        cache_key = f"season_windows_chrono_{season}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        windows = list(Window.objects.filter(season=season).only("id", "season", "date", "slot"))
        # Stable sort by date, slot, then id
        windows.sort(key=lambda w: (w.date, SLOT_ORDER.get(w.slot or "late", 3), w.id))

        infos = [
            WindowInfo(
                id=w.id,
                season=w.season,
                date=str(w.date),
                slot=w.slot or "unknown",
                chronological_index=i,
            )
            for i, w in enumerate(windows)
        ]
        # Cache for 5 minutes
        cache.set(cache_key, infos, 300)
        return infos

    def _get_previous_window(self) -> Optional[WindowInfo]:
        if not self.current_window or self.current_window.chronological_index == 0:
            return None
        return self.season_windows_cache[self.current_window.chronological_index - 1]

    def _get_later_windows(self) -> List[WindowInfo]:
        if not self.current_window:
            return []
        nxt = self.current_window.chronological_index + 1
        return self.season_windows_cache[nxt:] if nxt < len(self.season_windows_cache) else []

    def _calculate_user_deltas(self) -> List[UserDelta]:
        """
        Compute deltas for all users that should appear this window.
        Includes:
          - the full roster (ensures no-pick users still get rows and ranks),
          - users who made predictions in the current window,
          - anyone who appeared in previous or any season window (idempotent backfills).
        """
        # Resolve the games in this window once and get the week number
        games = Game.objects.filter(window_id=self.window_id).only("id", "week")
        game_ids = [g.id for g in games]

        # Get week number (all games in a window should have same week)
        week = games[0].week if games else 1
        ml_points = get_moneyline_points(week)

        # Users who actively touched this window (made any predictions here)
        current_window_users: Set[int] = set()
        if game_ids:
            current_window_users.update(
                MoneyLinePrediction.objects.filter(game_id__in=game_ids).values_list("user_id", flat=True)
            )
            current_window_users.update(
                PropBetPrediction.objects.filter(prop_bet__game_id__in=game_ids).values_list("user_id", flat=True)
            )

        # Users who already exist in the previous window (rank deltas will compare against these)
        previous_participants: Set[int] = set()
        prev_window = self._get_previous_window()
        if prev_window:
            previous_participants = set(
                UserWindowStat.objects.filter(window_id=prev_window.id).values_list("user_id", flat=True)
            )

        # Users who have stats anywhere this season (ensures idempotent replays)
        season_participants: Set[int] = set(
            UserWindowStat.objects.filter(window__season=self.current_window.season).values_list("user_id", flat=True)
        )

        # Full roster inclusion (key to fixing "no-pick users receive no row")
        roster_ids: Set[int] = _get_roster_user_ids()

        # Union of all sets
        relevant_user_ids = roster_ids | current_window_users | previous_participants | season_participants
        if not relevant_user_ids:
            return []

        # Correct counts by user for this window (absent => zero)
        ml_correct = dict(
            MoneyLinePrediction.objects
            .filter(game_id__in=game_ids, is_correct=True, user_id__in=relevant_user_ids)
            .values("user_id").annotate(count=Count("id")).values_list("user_id", "count")
        )
        pb_correct = dict(
            PropBetPrediction.objects
            .filter(prop_bet__game_id__in=game_ids, is_correct=True, user_id__in=relevant_user_ids)
            .values("user_id").annotate(count=Count("id")).values_list("user_id", "count")
        )

        # Previous window cumulative map (default 0 for first appearance)
        prev_cume_map: Dict[int, int] = {}
        if prev_window:
            prev_cume_map = dict(
                UserWindowStat.objects
                .filter(window_id=prev_window.id, user_id__in=relevant_user_ids)
                .values_list("user_id", "season_cume_points")
            )

        # Old cume at this window (needed to compute precise delta/idempotence)
        old_cume_map = dict(
            UserWindowStat.objects
            .filter(window_id=self.window_id, user_id__in=relevant_user_ids)
            .values_list("user_id", "season_cume_points")
        )

        # Assemble user deltas
        user_deltas: List[UserDelta] = []
        for user_id in relevant_user_ids:
            # Window points for this user (using week-based ML points)
            window_points = ml_correct.get(user_id, 0) * ml_points + pb_correct.get(user_id, 0) * PB_POINTS

            # New cumulative = previous cumulative + this window points
            prev_cume = prev_cume_map.get(user_id, 0)
            new_cume = prev_cume + window_points

            # Delta vs what was previously stored at this window (default 0)
            old_cume = old_cume_map.get(user_id, 0)
            delta = new_cume - old_cume

            user_deltas.append(UserDelta(user_id=user_id, old_cume=old_cume, new_cume=new_cume, delta=delta))
        return user_deltas

    def _update_current_window_stats(self, user_deltas: List[UserDelta]) -> None:
        """
        Upsert ml_correct/pb_correct/window_points and season_cume_points for all relevant users.
        Uses bulk upsert to be idempotent and fast.
        """
        if not user_deltas:
            return

        # Precompute correct counts again restricted to the users included in deltas
        games = Game.objects.filter(window_id=self.window_id).only("id", "week")
        game_ids = [g.id for g in games]

        # Get week number for this window
        week = games[0].week if games else 1
        ml_points = get_moneyline_points(week)

        user_ids = [ud.user_id for ud in user_deltas]

        ml_correct_map = dict(
            MoneyLinePrediction.objects
            .filter(game_id__in=game_ids, is_correct=True, user_id__in=user_ids)
            .values("user_id").annotate(count=Count("id")).values_list("user_id", "count")
        )
        pb_correct_map = dict(
            PropBetPrediction.objects
            .filter(prop_bet__game_id__in=game_ids, is_correct=True, user_id__in=user_ids)
            .values("user_id").annotate(count=Count("id")).values_list("user_id", "count")
        )

        # Build rows to upsert (no-pick => zeros)
        stats_to_upsert: List[UserWindowStat] = []
        for ud in user_deltas:
            mlc = ml_correct_map.get(ud.user_id, 0)
            pbc = pb_correct_map.get(ud.user_id, 0)
            window_points = mlc * ml_points + pbc * PB_POINTS

            stats_to_upsert.append(UserWindowStat(
                user_id=ud.user_id,
                window_id=self.window_id,
                ml_correct=mlc,
                pb_correct=pbc,
                window_points=window_points,
                season_cume_points=ud.new_cume,
                rank_dense=0,
                rank_delta=0,
            ))

        # Django 5.1+: bulk upsert on (user, window)
        UserWindowStat.objects.bulk_create(
            stats_to_upsert,
            update_conflicts=True,
            update_fields=["ml_correct", "pb_correct", "window_points", "season_cume_points"],
            unique_fields=["user", "window"],
        )

    def _propagate_deltas_forward(self, user_deltas: List[UserDelta]) -> None:
        """
        Add each user's delta to all later windows in-season, keeping season_cume_points consistent
        after edits or late resolutions.
        """
        later = self._get_later_windows()
        if not later:
            return
        later_ids = [w.id for w in later]

        for ud in user_deltas:
            if ud.delta == 0:
                continue
            UserWindowStat.objects.filter(
                user_id=ud.user_id, window_id__in=later_ids
            ).update(season_cume_points=F("season_cume_points") + ud.delta)

    def _update_rankings(self) -> None:
        """
        Compute dense rank for this window based on season_cume_points and write rank deltas
        against the previous window's ranks. Users without a prior row implicitly have delta 0.
        """
        current_stats = list(
            UserWindowStat.objects.filter(window_id=self.window_id).order_by("-season_cume_points", "user_id")
        )
        if not current_stats:
            return

        prev = self._get_previous_window()
        prev_ranks: Dict[int, int] = {}
        if prev:
            prev_ranks = dict(
                UserWindowStat.objects.filter(window_id=prev.id).values_list("user_id", "rank_dense")
            )

        updates: List[UserWindowStat] = []
        prev_points = None
        points_seen = 0  # number of unique point levels processed (dense rank counter)

        for stat in current_stats:
            if prev_points is None:
                prev_points = stat.season_cume_points
                points_seen = 1
            elif stat.season_cume_points < prev_points:
                points_seen += 1
                prev_points = stat.season_cume_points
            current_rank = points_seen

            # Rank delta: positive means improvement versus previous window rank
            prev_rank = prev_ranks.get(stat.user_id)
            rank_delta = (prev_rank - current_rank) if prev_rank is not None else 0

            if stat.rank_dense != current_rank or stat.rank_delta != rank_delta:
                stat.rank_dense = current_rank
                stat.rank_delta = rank_delta
                updates.append(stat)

        if updates:
            UserWindowStat.objects.bulk_update(updates, ["rank_dense", "rank_delta"])

    def _update_window_completeness(self) -> None:
        """
        Flip completeness based on whether all games and props are resolved, guarded by a row lock.
        """
        try:
            w = Window.objects.select_for_update().get(pk=self.window_id)
        except Window.DoesNotExist:
            # Already validated earlier, but be defensive
            raise WindowCalculationError(f"Window {self.window_id} does not exist")

        games = Game.objects.filter(window_id=self.window_id)

        # If no games exist, ensure window is not complete
        if not games.exists():
            if w.is_complete:
                w.is_complete = False
                w.completed_at = None
                w.save(update_fields=["is_complete", "completed_at", "updated_at"])
            return

        unresolved_games = games.filter(winner__isnull=True).exists()
        unresolved_props = PropBet.objects.filter(game__window_id=self.window_id, correct_answer__isnull=True).exists()
        is_complete = not (unresolved_games or unresolved_props)

        if is_complete and not w.is_complete:
            w.is_complete = True
            w.completed_at = timezone.now()
            w.save(update_fields=["is_complete", "completed_at", "updated_at"])
        elif not is_complete and w.is_complete:
            w.is_complete = False
            w.completed_at = None
            w.save(update_fields=["is_complete", "completed_at", "updated_at"])


# ------------------------------- Public API --------------------------------

@transaction.atomic
def recompute_window_optimized(window_id: int, *, actor=None) -> None:
    """
    OPTIMIZED window recomputation with security:
      - Optional permission gate via 'actor'
      - Per-window mutex & small throttle
      - Full transactional safety
    """
    calculator = OptimizedWindowCalculator(window_id, actor=actor)
    calculator.recompute_window()


def bulk_recompute_windows_optimized(window_ids: List[int], *, actor=None) -> Dict[int, bool]:
    """
    Bulk recompute multiple windows in chronological order.
    Enforces the same permission check and per-window mutex/throttle.
    Returns dict of window_id -> success bool.
    """
    # Authorization check once up-front; individual calls re-check too
    _assert_permission(actor)

    results: Dict[int, bool] = {}
    windows = Window.objects.filter(id__in=window_ids).only("id", "season", "date", "slot")

    # Derive chronological order per season
    sortable: List[tuple[int, int]] = []
    for window in windows:
        season_windows = Window.objects.filter(season=window.season).only("id", "date", "slot")
        ordered = sorted(season_windows, key=lambda w: (w.date, SLOT_ORDER.get(w.slot or "late", 3), w.id))
        idx = next((i for i, w in enumerate(ordered) if w.id == window.id), -1)
        sortable.append((window.id, idx))
    sortable.sort(key=lambda x: x[1])

    for wid, _ in sortable:
        try:
            recompute_window_optimized(wid, actor=actor)
            results[wid] = True
        except Exception as e:
            logger.error("Failed to recompute window %s: %s", wid, str(e))
            results[wid] = False
    return results


def validate_window_calculations(window_id: int) -> Dict[str, Any]:
    """
    Diagnostic consistency checker for a window.
    Adds a roster coverage check to ensure every roster user has a UserWindowStat row.
    """
    try:
        window = Window.objects.get(id=window_id)
        games = Game.objects.filter(window_id=window_id)
        stats = UserWindowStat.objects.filter(window_id=window_id)

        unresolved_games = games.filter(winner__isnull=True).count()
        total_games = games.count()

        total_props = PropBet.objects.filter(game__window_id=window_id).count()
        unresolved_props = PropBet.objects.filter(
            game__window_id=window_id,
            correct_answer__isnull=True
        ).count()

        users_with_predictions = set()
        users_with_predictions.update(
            MoneyLinePrediction.objects.filter(game__window_id=window_id).values_list("user_id", flat=True)
        )
        users_with_predictions.update(
            PropBetPrediction.objects.filter(prop_bet__game__window_id=window_id).values_list("user_id", flat=True)
        )
        users_with_stats = set(stats.values_list("user_id", flat=True))

        # Roster coverage (ensures no-pick users are represented)
        roster = _get_roster_user_ids()
        missing_from_roster = roster - users_with_stats

        return {
            "window_id": window_id,
            "season": window.season,
            "is_complete": window.is_complete,
            "games": {"total": total_games, "resolved": total_games - unresolved_games, "unresolved": unresolved_games},
            "props": {"total": total_props, "resolved": total_props - unresolved_props, "unresolved": unresolved_props},
            "users": {
                "with_predictions": len(users_with_predictions),
                "with_stats": len(users_with_stats),
                "missing_stats_from_predictions": list(users_with_predictions - users_with_stats),
                "missing_stats_from_roster": list(missing_from_roster),
            },
            "validation_passed": (
                unresolved_games == 0 and unresolved_props == 0 and
                len(users_with_predictions - users_with_stats) == 0 and
                len(missing_from_roster) == 0
            ),
        }
    except Exception as e:
        return {"window_id": window_id, "error": str(e), "validation_passed": False}


# ---------------------------- Best category helper -------------------------

from django.db.models import F as _F

BEST_BALANCED_MARGIN = 0.02  # 2 percentage points

def compute_best_category_for_user(user, season: int):
    """
    Determine a user's best category for the season using resolved counts.
    Denominators are all resolved items (missed picks count as incorrect).
    """
    # Totals of resolved items
    total_ml_resolved = Game.objects.filter(season=season, winner__isnull=False).count()
    total_pb_resolved = PropBet.objects.filter(game__season=season, correct_answer__isnull=False).count()

    # Correct counts (missed picks count as incorrect because denominator is all resolved)
    ml_correct = (
        MoneyLinePrediction.objects
        .filter(user=user, game__season=season, game__winner__isnull=False, predicted_winner=_F("game__winner"))
        .count()
        if total_ml_resolved else 0
    )
    pb_correct = (
        PropBetPrediction.objects
        .filter(user=user, prop_bet__game__season=season, prop_bet__correct_answer__isnull=False,
                answer=_F("prop_bet__correct_answer"))
        .count()
        if total_pb_resolved else 0
    )

    # Accuracies (0..1)
    ml_acc = (ml_correct / total_ml_resolved) if total_ml_resolved else None
    pb_acc = (pb_correct / total_pb_resolved) if total_pb_resolved else None

    # Decide best category
    if ml_acc is None and pb_acc is None:
        return {"bestCategory": None, "bestCategoryAccuracy": 0}

    if ml_acc is not None and pb_acc is None:
        return {"bestCategory": "Moneyline", "bestCategoryAccuracy": round(ml_acc * 100, 1)}
    if pb_acc is not None and ml_acc is None:
        return {"bestCategory": "Prop Bets", "bestCategoryAccuracy": round(pb_acc * 100, 1)}

    # Both exist: compare with margin
    diff = abs(ml_acc - pb_acc)
    if diff <= BEST_BALANCED_MARGIN or (ml_acc >= 0.65 and pb_acc >= 0.65):
        return {"bestCategory": "Balanced", "bestCategoryAccuracy": round(max(ml_acc, pb_acc) * 100, 1)}

    if ml_acc > pb_acc:
        return {"bestCategory": "Moneyline", "bestCategoryAccuracy": round(ml_acc * 100, 1)}
    else:
        return {"bestCategory": "Prop Bets", "bestCategoryAccuracy": round(pb_acc * 100, 1)}
