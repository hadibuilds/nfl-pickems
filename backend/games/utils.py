# backend/games/utils.py
from __future__ import annotations
from django.utils import timezone
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")

def slot_for(dt_utc) -> str:
    dt_pt = timezone.localtime(dt_utc, PACIFIC)
    h = dt_pt.hour
    if h < 13:
        return "morning"
    elif h < 17:
        return "afternoon"
    return "late"

def ensure_window_for_game(season: int, start_time_utc):
    # Lazy import to avoid circular import at app load time
    from django.apps import apps
    Window = apps.get_model("games", "Window")

    dt_pt = timezone.localtime(start_time_utc, PACIFIC)
    return Window.objects.get_or_create(
        season=season,
        date=dt_pt.date(),
        slot=slot_for(start_time_utc),
        defaults={}
    )[0]
