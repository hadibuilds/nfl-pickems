# take an after-window snapshot when all results in that window are entered

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache

from .models import PropBet, Top3Snapshot
from games.models import Game
from .services.top3_sql import snapshot_and_publish, publish_top3_from_db


logger = logging.getLogger(__name__)
PACIFIC = ZoneInfo("America/Los_Angeles")

BEFORE_FLAG = "top3:before_taken:{wk}"
BEFORE_TTL = 60 * 60 * 12  # 12h; adjust if you want


def _take_before_snapshot_if_needed(window_key: str):
    """
    Called inside pre_save, BEFORE the DB row changes.
    publish_top3_from_db() reads current DB state (so it's truly 'before').
    """
    if not window_key:
        return
    # Fast, process-wide gate
    if not cache.add(BEFORE_FLAG.format(wk=window_key), 1, timeout=BEFORE_TTL):
        return  # someone already took it recently

    # Double-check at DB level (in case cache was flushed)
    if Top3Snapshot.objects.filter(window_key=window_key).exists():
        return

    # Take the BEFORE snapshot: publish live Top-3 (no version offset needed)
    data = publish_top3_from_db()
    Top3Snapshot.objects.create(window_key=window_key, version=1, payload=data)

def _get_prev(instance) -> Optional[Any]:
    if not instance.pk:
        return None
    try:
        return instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return None

def _slot_for_local_time(dt_local):
    h = dt_local.hour
    return "morning" if h < 13 else "afternoon" if h < 17 else "late"

def _window_bounds_for_game(game: Game):
    start_dt = getattr(game, "start_time", None)
    if not start_dt:
        return None
    local_dt = timezone.localtime(start_dt, PACIFIC)
    date_only = local_dt.date()
    slot = _slot_for_local_time(local_dt)

    day_start = datetime(date_only.year, date_only.month, date_only.day, 0, 0, tzinfo=PACIFIC)
    morning_end = day_start + timedelta(hours=13)
    afternoon_end = day_start + timedelta(hours=17)
    day_end = day_start + timedelta(days=1)

    if slot == "morning":
        ws, we = day_start, morning_end
    elif slot == "afternoon":
        ws, we = morning_end, afternoon_end
    else:
        ws, we = afternoon_end, day_end

    return (f"{date_only.isoformat()}:{slot}", ws, we)

def _games_qs_for_same_window(game: Game):
    info = _window_bounds_for_game(game)
    if not info:
        return Game.objects.none()
    _, ws, we = info
    return Game.objects.filter(start_time__gte=ws, start_time__lt=we)

def _window_complete(games_qs) -> bool:
    total_games = games_qs.count()
    # winner must be non-null AND non-empty
    winners_done = games_qs.exclude(Q(winner=None) | Q(winner="")).count()

    from predictions.models import PropBet
    props_qs = PropBet.objects.filter(game__in=games_qs)
    total_props = props_qs.count()
    # prop answer must be non-null AND non-empty
    props_done = props_qs.exclude(Q(correct_answer=None) | Q(correct_answer="")).count()

    return (total_games > 0) and (winners_done == total_games) and (props_done == total_props)

def _window_key_for_game(game: Game) -> Optional[str]:
    info = _window_bounds_for_game(game)
    return info[0] if info else None

@receiver(pre_save, sender=Game)
def _on_game_winner_change(sender, instance: Game, **kwargs):
    prev = _get_prev(instance)
    if not prev:
        return
    prev_winner = getattr(prev, "winner", None)
    curr_winner = getattr(instance, "winner", None)
    if prev_winner == curr_winner or curr_winner is None:
        return

    # BEFORE snapshot (pre-save = reads state before this change)
    wk = _window_key_for_game(instance)
    _take_before_snapshot_if_needed(wk)

    # AFTER snapshot (only when window completes)
    def _after_commit():
        games_qs = _games_qs_for_same_window(instance)
        if _window_complete(games_qs):
            if wk:
                # This will create version 2 if version 1 already exists;
                # if someone forced an early snapshot, it'll just bump the version.
                snapshot_and_publish(wk)
                logger.info("AFTER snapshot taken for complete window: %s", wk)

    transaction.on_commit(_after_commit)

@receiver(pre_save, sender=PropBet)
def _on_propbet_answer_change(sender, instance: PropBet, **kwargs):

    prev = _get_prev(instance)
    if not prev:
        return
    prev_ans = getattr(prev, "correct_answer", None)
    curr_ans = getattr(instance, "correct_answer", None)
    if prev_ans == curr_ans or curr_ans in (None, ""):
        return

    game = getattr(instance, "game", None)
    if not game:
        return

    wk = _window_key_for_game(game)
    _take_before_snapshot_if_needed(wk)

    def _after_commit():
        games_qs = _games_qs_for_same_window(game)
        if _window_complete(games_qs):
            if wk:
                snapshot_and_publish(wk)
                logger.info("AFTER snapshot taken for complete window: %s", wk)

    transaction.on_commit(_after_commit)

@receiver(pre_save, sender=Game)
def _apply_game_window_key(sender, instance, **kwargs):
    if instance.start_time:
        pt = timezone.localtime(instance.start_time, PACIFIC)
        instance.window_key = f"{pt.date().isoformat()}:{_slot_for_local_time(pt)}"

@receiver(pre_save, sender=PropBet)
def _apply_prop_window_key(sender, instance, **kwargs):
    if getattr(instance, "game", None) and getattr(instance.game, "window_key", None):
        instance.window_key = instance.game.window_key