from __future__ import annotations

import logging
from datetime import timedelta
from datetime import timezone as dt_timezone  # ✅ use Python's UTC tzinfo

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, F, UniqueConstraint, Index, Case, When, IntegerField
from django.utils import timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

PACIFIC = ZoneInfo("America/Los_Angeles")

WINDOW_SLOTS = (
    ("morning", "Morning"),
    ("afternoon", "Afternoon"),
    ("late", "Late"),
)

SLOT_ORDER = {"morning": 0, "afternoon": 1, "late": 2}


class Window(models.Model):
    season = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)  # PT calendar date
    slot = models.CharField(max_length=16, choices=WINDOW_SLOTS, db_index=True)
    is_complete = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # handy for cache keys

    class Meta:
        constraints = [
            UniqueConstraint(fields=["season", "date", "slot"], name="uniq_window_season_date_slot"),
        ]
        indexes = [
            Index(fields=["season", "date", "slot"]),
            Index(fields=["season", "is_complete", "date"]),
        ]
        ordering = ["season", "date", "slot"]

    def __str__(self) -> str:
        suffix = " (complete)" if self.is_complete else " (open)"
        return f"{self.date.isoformat()} {self.slot}{suffix}"

    @classmethod
    def previous_completed(cls, season: int, date, slot: str) -> "Window | None":
        """Find the most recent completed window strictly before (season, date, slot)."""
        slot_rank_expr = Case(
            When(slot="morning", then=models.Value(0)),
            When(slot="afternoon", then=models.Value(1)),
            When(slot="late", then=models.Value(2)),
            output_field=IntegerField(),
        )
        cur_rank = SLOT_ORDER[slot]
        return (
            cls.objects.filter(season=season, is_complete=True)
            .annotate(_rank=slot_rank_expr)
            .filter(Q(date__lt=date) | Q(date=date, _rank__lt=cur_rank))
            .order_by("-date", "-_rank")
            .first()
        )


class Game(models.Model):
    season = models.IntegerField(db_index=True)
    week = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    start_time = models.DateTimeField(help_text="UTC")
    locked = models.BooleanField(default=False, help_text="Manual override")
    winner = models.CharField(max_length=50, null=True, blank=True)
    window = models.ForeignKey(Window, on_delete=models.PROTECT, related_name="games")

    # Team records going into this game (pre-calculated for performance)
    home_team_record = models.CharField(max_length=20, blank=True, default="", help_text="W-L or W-L-T")
    away_team_record = models.CharField(max_length=20, blank=True, default="", help_text="W-L or W-L-T")

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["season", "week", "home_team", "away_team"],
                name="uniq_game_season_week_matchup",
            ),
            models.CheckConstraint(
                check=~Q(home_team=F("away_team")),
                name="chk_home_away_not_equal",
            ),
            models.CheckConstraint(
                name="chk_winner_is_team",
                check=(
                    Q(winner__isnull=True) |
                    Q(winner=F("home_team")) |
                    Q(winner=F("away_team")) |
                    Q(winner="TIE")
                ),
            ),
        ]
        indexes = [
            Index(fields=["season", "week", "start_time"]),
            Index(fields=["season", "window", "start_time"]),
        ]
        ordering = ["season", "week", "start_time"]

    def __str__(self) -> str:
        st = self.start_time.isoformat() if self.start_time else "—"
        return f"W{self.week}: {self.away_team} @ {self.home_team} ({st})"

    @property
    def is_locked(self) -> bool:
        now = timezone.now()
        return bool(self.locked or (self.start_time and now >= self.start_time))

    def clean(self):
        # ✅ start_time must be timezone-aware (reject naive)
        if self.start_time is not None and timezone.is_naive(self.start_time):
            raise ValidationError({"start_time": "start_time must be timezone-aware."})

        # ✅ prevent moving a started game to a different window
        if self.pk:
            old = type(self).objects.only("window_id", "start_time").get(pk=self.pk)
            if old.window_id != self.window_id and self.start_time and timezone.now() >= self.start_time:
                raise ValidationError("Cannot move a started game to a different window.")

        # ❌ Do NOT enforce UTC via utcoffset here; we normalize in save()

    # ✅ Normalize to canonical UTC on write (covers admin, scripts, API)
    def save(self, *args, **kwargs):
        if self.start_time and timezone.is_aware(self.start_time):
            self.start_time = self.start_time.astimezone(dt_timezone.utc)
        super().save(*args, **kwargs)

    @transaction.atomic
    def finalize(self, winner: str | None):
        """
        Set winner and grade money-line predictions for this game only,
        then recompute the window. Atomic by design.
        """
        from analytics.services.window_stats_optimized import recompute_window_optimized  # lazy import
        from predictions.models import MoneyLinePrediction
        from django.core.cache import cache

        # Save winner (validation already enforced by clean() / constraint)
        self.winner = winner
        self.save(update_fields=["winner"])

        # Grade ML predictions for this game
        if winner is None:
            # clearing winner → unset correctness
            MoneyLinePrediction.objects.filter(game=self).update(is_correct=None)
        else:
            MoneyLinePrediction.objects.filter(game=self).update(
                is_correct=models.Case(
                    When(predicted_winner=winner, then=models.Value(True)),
                    default=models.Value(False),
                    output_field=models.BooleanField(),
                )
            )

        # Update team records for next week's games when this game is finalized
        def _update_team_records_for_next_week():
            """
            When a game result is entered, update the team records for both teams
            in all games they play in future weeks.
            """
            next_week = self.week + 1

            # Get games for both teams in the next week
            next_week_games = Game.objects.filter(
                season=self.season,
                week=next_week
            ).filter(
                Q(home_team=self.home_team) | Q(away_team=self.home_team) |
                Q(home_team=self.away_team) | Q(away_team=self.away_team)
            )

            for game in next_week_games:
                # Calculate updated records for this team going into next week
                for team in [game.home_team, game.away_team]:
                    record = _calculate_team_record(team, self.season, next_week)
                    if team == game.home_team:
                        game.home_team_record = record
                    else:
                        game.away_team_record = record

                game.save(update_fields=['home_team_record', 'away_team_record'])

        def _calculate_team_record(team_name: str, season: int, up_to_week: int) -> str:
            """Calculate W-L-T record for a team up to (but not including) a given week."""
            team_games = Game.objects.filter(
                season=season,
                week__lt=up_to_week,
                winner__isnull=False
            ).filter(
                Q(home_team=team_name) | Q(away_team=team_name)
            )

            wins = team_games.filter(winner=team_name).count()
            ties = team_games.filter(winner="TIE").count()
            total = team_games.count()
            losses = total - wins - ties

            if ties > 0:
                return f"{wins}-{losses}-{ties}"
            return f"{wins}-{losses}"

        # Recompute stats for this window (log on failure instead of crashing admin)
        def _safe_recompute():
            try:
                _update_team_records_for_next_week()
                recompute_window_optimized(self.window_id)
            except Exception:
                logger.exception("Window recompute failed for window_id=%s (game_id=%s)", self.window_id, self.pk)

        transaction.on_commit(_safe_recompute)


class PropBet(models.Model):
    CATEGORY_CHOICES = [
        ("over_under", "Over/Under"),
        ("point_spread", "Point Spread"),
        ("take_the_bait", "Take-the-Bait"),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="prop_bets")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=100, null=True, blank=True)

    @property
    def option_a(self):
        try:
            return (self.options or [None, None])[0]
        except Exception:
            return None

    @property
    def option_b(self):
        try:
            return (self.options or [None, None])[1]
        except Exception:
            return None

    # Optional denorms (copy from game in importers if you add them)
    # season = models.IntegerField(db_index=True, null=True, blank=True)
    # week = models.IntegerField(db_index=True, null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["game", "question"], name="uniq_probet_game_question"),
        ]
        indexes = [
            Index(fields=["game", "category"]),
        ]
        ordering = ["game_id", "id"]

    def __str__(self) -> str:
        return f"[{self.category}] {self.question}"

    @property
    def is_locked(self) -> bool:
        return self.game.is_locked

    @transaction.atomic
    def grade(self, correct_answer: str | None):
        """Set correct answer and grade prop-bet predictions for this prop only, then recompute."""
        from analytics.services.window_stats_optimized import recompute_window_optimized
        from predictions.models import PropBetPrediction

        self.correct_answer = correct_answer
        self.save(update_fields=["correct_answer"])

        if correct_answer is None:
            PropBetPrediction.objects.filter(prop_bet=self).update(is_correct=None)
        else:
            PropBetPrediction.objects.filter(prop_bet=self).update(
                is_correct=models.Case(
                    When(answer=correct_answer, then=models.Value(True)),
                    default=models.Value(False),
                    output_field=models.BooleanField(),
                )
            )

        def _safe_recompute():
            try:
                recompute_window_optimized(self.game.window_id)
            except Exception:
                logger.exception(
                    "Prop recompute failed for window_id=%s (prop_id=%s, game_id=%s)",
                    self.game.window_id, self.pk, self.game_id
                )

        transaction.on_commit(_safe_recompute)
