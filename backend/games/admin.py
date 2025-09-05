# admin.py (drop-in)
from django import forms
from django.contrib import admin, messages
from django.db import transaction, IntegrityError
import logging

from django.utils import timezone                      # ✅ for awareness checks
from datetime import timezone as dt_timezone            # ✅ Django 5+: use Python's UTC
from zoneinfo import ZoneInfo                           # ✅ for PT window logic
from datetime import datetime

from .models import Window, Game, PropBet
from analytics.services.window_stats_optimized import (
    recompute_window_optimized,
    WindowCalculationError,
)

logger = logging.getLogger(__name__)

# ---------- Helpers for window derivation (PT rules) ----------
PACIFIC = ZoneInfo("America/Los_Angeles")

def slot_for_pacific_time(dt_pt: datetime) -> str:
    """
    Slot rules (PT):
      - morning:   kickoff before 1:00 PM PT
      - afternoon: 1:00 PM PT to 4:59 PM PT (inclusive of 5:00 exactly in your prior logic)
      - late:      5:00 PM PT or later
    """
    h, m = dt_pt.hour, dt_pt.minute
    if h < 13:
        return "morning"
    if h < 17 or (h == 17 and m == 0):
        return "afternoon"
    return "late"

def ensure_window_for(season: int, start_time_utc: datetime) -> Window:
    """Map a UTC kickoff to a Window keyed by its Pacific date + slot."""
    start_pt = start_time_utc.astimezone(PACIFIC)
    window_date = start_pt.date()
    slot = slot_for_pacific_time(start_pt)
    win, _ = Window.objects.get_or_create(
        season=season,
        date=window_date,
        slot=slot,
        defaults={"is_complete": False},
    )
    return win

def derive_season_from_kickoff(start_time_utc: datetime) -> int:
    """NFL season: Jan–Feb belong to the *previous* year; Mar–Dec to the current year (in PT)."""
    dt_pt = start_time_utc.astimezone(PACIFIC)
    return (dt_pt.year - 1) if dt_pt.month in (1, 2) else dt_pt.year


# ---------- Forms with safe, dynamic dropdowns ----------

class GameAdminForm(forms.ModelForm):
    """Winner must be either home_team or away_team (or cleared)."""
    winner = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = Game
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        home = self.instance.home_team if self.instance and self.instance.pk else (
            self.data.get("home_team") or self.initial.get("home_team")
        )
        away = self.instance.away_team if self.instance and self.instance.pk else (
            self.data.get("away_team") or self.initial.get("away_team")
        )

        choices = [("", "— Clear —")]
        if home:
            choices.append((home, home))
        if away and away != home:
            choices.append((away, away))
        self.fields["winner"].choices = choices
        self.fields["winner"].widget = forms.Select(choices=choices)

    def clean_winner(self):
        win = self.cleaned_data.get("winner")
        home = self.cleaned_data.get("home_team") or (self.instance.home_team if self.instance else None)
        away = self.cleaned_data.get("away_team") or (self.instance.away_team if self.instance else None)
        if win in ("", None):
            return None
        if win not in {home, away}:
            raise forms.ValidationError("Winner must match the home or away team.")
        return win

    # ✅ Normalize to UTC (Python's tz) and reject naive datetimes
    def clean_start_time(self):
        dt = self.cleaned_data.get("start_time")
        if dt is None:
            return dt
        if timezone.is_naive(dt):
            raise forms.ValidationError("start_time must be timezone-aware")
        return dt.astimezone(dt_timezone.utc)


class PropBetAdminForm(forms.ModelForm):
    """Correct answer must be one of options (JSON array) or cleared."""
    correct_answer = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = PropBet
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opts = []
        if self.instance and getattr(self.instance, "options", None):
            if isinstance(self.instance.options, list):
                opts = self.instance.options
        choices = [("", "— Clear —")] + [(o, o) for o in opts]
        self.fields["correct_answer"].choices = choices
        self.fields["correct_answer"].widget = forms.Select(choices=choices)

    def clean_correct_answer(self):
        ans = self.cleaned_data.get("correct_answer")
        opts = self.cleaned_data.get("options") or []
        if ans in ("", None):
            return None
        if isinstance(opts, list) and ans not in opts:
            raise forms.ValidationError("Correct answer must be one of the defined options.")
        return ans


# ---------- Admin registrations ----------

@admin.register(Window)
class WindowAdmin(admin.ModelAdmin):
    list_display = ("season", "date", "slot", "is_complete", "completed_at", "updated_at")
    list_filter = ("season", "slot", "is_complete")
    search_fields = ("date",)
    actions = ["refresh_status", "recompute_selected_windows"]

    @admin.action(description="Refresh status (recompute window stats)")
    def refresh_status(self, request, queryset):
        affected_ids = {w.id for w in queryset}
        def _do():
            for wid in affected_ids:
                try:
                    recompute_window_optimized(wid, actor=request.user)
                except WindowCalculationError:
                    logger.info("Refresh throttled for window %s", wid)
                except Exception:
                    logger.exception("Refresh failed for window %s", wid)
        transaction.on_commit(_do)
        self.message_user(request, f"Scheduled recompute for {len(affected_ids)} window(s).", messages.SUCCESS)

    @admin.action(description="Recompute selected window(s) now")
    def recompute_selected_windows(self, request, queryset):
        affected_ids = {w.id for w in queryset}
        def _do():
            for wid in affected_ids:
                try:
                    recompute_window_optimized(wid, actor=request.user)
                except WindowCalculationError:
                    logger.info("Manual recompute throttled for window %s", wid)
                except Exception:
                    logger.exception("Manual recompute failed for window %s", wid)
        transaction.on_commit(_do)
        self.message_user(request, f"Scheduled recompute for {len(affected_ids)} window(s).", messages.SUCCESS)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    list_display = (
        "week", "home_team", "away_team", "start_time",
        "is_locked_display", "winner", "window", "season",
    )
    ordering = ("start_time", "week")
    list_filter = ("season", "week", "locked", "window")
    search_fields = ("home_team", "away_team")
    actions = ["finalize_selected"]

    class Media:
        js = ("games/admin_winner_choices.js",)

    @admin.display(boolean=True, description="Locked?")
    def is_locked_display(self, obj: Game):
        return obj.is_locked

    def save_model(self, request, obj: Game, form, change):
        prev_winner = None
        prev_window_id = None
        if change:
            try:
                old = type(obj).objects.only("winner", "window_id", "start_time").get(pk=obj.pk)
                prev_winner = old.winner
                prev_window_id = old.window_id
            except type(obj).DoesNotExist:
                prev_winner = None
                prev_window_id = None

        # ✅ Ensure season & window from kickoff (so the form doesn't need them)
        if obj.start_time and not obj.season:
            obj.season = derive_season_from_kickoff(obj.start_time)
        if obj.start_time and obj.season:
            obj.window = ensure_window_for(obj.season, obj.start_time)

        try:
            super().save_model(request, obj, form, change)
        except IntegrityError as e:
            logger.exception("Game save failed (IntegrityError).")
            self.message_user(request, f"Save failed: {e}", messages.ERROR)
            return
        except Exception:
            logger.exception("Game save failed (admin).")
            self.message_user(request, "Save failed — see server logs for details.", messages.ERROR)
            return

        # Decide what changed
        winner_changed = (not change) or (prev_winner != obj.winner)
        window_changed = change and prev_window_id and (prev_window_id != obj.window_id)

        # Grade & schedule recompute via model hook
        if winner_changed:
            try:
                obj.finalize(obj.winner)  # grades ML + schedules recompute for obj.window_id
            except Exception:
                logger.exception("Finalize failed for game_id=%s", obj.pk)
                self.message_user(request, "Saved, but finalize failed — check logs.", messages.ERROR)

        # If the game moved windows, also recompute the previous window
        if window_changed:
            def _do_prev():
                try:
                    recompute_window_optimized(prev_window_id, actor=request.user)
                except WindowCalculationError:
                    logger.info("Prev window recompute throttled for %s", prev_window_id)
                except Exception:
                    logger.exception("Prev window recompute failed for %s", prev_window_id)
            transaction.on_commit(_do_prev)

        if winner_changed or window_changed:
            self.message_user(request, "Window stats updated.", messages.SUCCESS)

    @admin.action(description="Finalize selected games (grade & recompute)")
    def finalize_selected(self, request, queryset):
        count = 0
        for g in queryset.select_related("window"):
            try:
                g.finalize(g.winner)
                count += 1
            except Exception:
                logger.exception("Finalize failed for game_id=%s (bulk action)", g.pk)
        self.message_user(request, f"Finalized {count} game(s). Recompute scheduled.", messages.SUCCESS)


@admin.register(PropBet)
class PropBetAdmin(admin.ModelAdmin):
    form = PropBetAdminForm
    list_display = ("game", "category", "question", "correct_answer")
    list_filter = ("category", "game__season", "game__week")
    search_fields = ("question",)
    actions = ["grade_selected"]

    class Media:
        js = ("games/admin_propbet_choices.js",)

    def save_model(self, request, obj: PropBet, form, change):
        prev_correct = None
        if change:
            try:
                old = type(obj).objects.only("correct_answer").get(pk=obj.pk)
                prev_correct = old.correct_answer
            except type(obj).DoesNotExist:
                prev_correct = None

        try:
            super().save_model(request, obj, form, change)

            # Fixed: Also call grade() when answer is cleared (set to None)
            answer_changed = (not change and obj.correct_answer is not None) or (change and prev_correct != obj.correct_answer)
            if answer_changed:
                try:
                    obj.grade(obj.correct_answer)  # grades props + schedules recompute for obj.game.window_id
                    self.message_user(request, "Window stats updated.", messages.SUCCESS)
                except Exception:
                    logger.exception("Prop grade failed for prop_id=%s", obj.pk)
                    self.message_user(request, "Saved, but grading failed — check logs.", messages.ERROR)

        except Exception:
            logger.exception("Prop save failed (admin).")
            self.message_user(request, "Save failed — see server logs for details.", messages.ERROR)
