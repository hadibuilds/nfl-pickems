from django.db import models
from django.db.models import Q, F, Value, BooleanField, Case, When, IntegerField
from django.db.models import UniqueConstraint
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Los_Angeles")

WINDOW_SLOTS = (("morning","Morning"),("afternoon","Afternoon"),("late","Late"))
SLOT_ORDER = {"morning": 0, "afternoon": 1, "late": 2}

class Game(models.Model):
    season = models.PositiveSmallIntegerField(db_index=True)
    week = models.PositiveSmallIntegerField(db_index=True)
    home_team = models.CharField(max_length=50, db_index=True)
    away_team = models.CharField(max_length=50, db_index=True)
    start_time = models.DateTimeField(db_index=True)
    locked = models.BooleanField(default=False)  # Manual override
    winner = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    window = models.ForeignKey("games.Window", on_delete=models.PROTECT, related_name="games",
                               null=False, blank=True, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["season", "week", "home_team", "away_team"],
                name="uq_game_season_week_home_away",
            ),
            models.CheckConstraint(
                check=~Q(home_team=F("away_team")),
                name="ck_game_home_neq_away",
            ),
        ]
        indexes = [
            models.Index(fields=["season", "week", "start_time"], name="ix_game_sched"),
        ]
    
    def clean(self):
        if self.winner and self.winner not in (self.home_team, self.away_team):
            raise ValidationError("winner must be either home_team or away_team")
    
    @property
    def is_locked(self) -> bool:
        # Manual override always wins
        if self.locked:
            return True
        # If start_time isn't set yet (e.g., admin add form), treat as unlocked
        if not self.start_time:
            return False
        return timezone.now() >= self.start_time
    
    def _compute_window_parts(self):
        dt_pt = timezone.localtime(self.start_time, PACIFIC)
        h = dt_pt.hour
        slot = "morning" if h < 13 else ("afternoon" if h < 17 else "late")
        return dt_pt.date(), slot

    def save(self, *args, **kwargs):
        """
        Keep window assignment in sync and, when the winner changes,
        grade money-line predictions in bulk. Single save + atomic.
        """
        # --- 1) attach window BEFORE saving ---
        if self.start_time and self.season:
            d, slot = self._compute_window_parts()
            w, _ = Window.objects.get_or_create(season=self.season, date=d, slot=slot)
            self.window = w  # PROTECT on the FK is recommended

        # --- 2) detect winner change BEFORE saving (read current DB value) ---
        winner_before = None
        if self.pk:
            winner_before = (
                type(self)
                .objects.only("winner")
                .filter(pk=self.pk)
                .values_list("winner", flat=True)
                .first()
            )

        # --- 3) single save ---
        with transaction.atomic():
            super().save(*args, **kwargs)

            # --- 4) cascade only if winner actually changed ---
            if winner_before != self.winner:
                from predictions.models import Prediction  # or MoneyLinePrediction if renamed

                if self.winner is None:
                    Prediction.objects.filter(game=self).update(is_correct=None)
                else:
                    Prediction.objects.filter(game=self).update(
                        is_correct=Case(
                            When(predicted_winner=self.winner, then=Value(True)),
                            default=Value(False),
                            output_field=BooleanField(),
                        )
                    )

    def __str__(self):
        status = "🔒" if self.is_locked else ""
        window = self.window if self.window else ""
        return f"{status} Week {self.week}: {self.away_team} @ {self.home_team} {self.season}"

class PropBet(models.Model):
    CATEGORY_CHOICES = [
        ('over_under', 'Over/Under'),
        ('point_spread', 'Point Spread'),
        ('take_the_bait', 'Take-the-Bait')
    ]

    game = models.ForeignKey("games.Game", on_delete=models.CASCADE, related_name="prop_bets", db_index=True, null=False)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    # Optional denormalizations for fast filters/joins
    season = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    week = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["game", "question"], name="uq_propbet_game_question"),
        ]
        indexes = [
            models.Index(fields=["game", "category"], name="ix_propbet_game_cat"),
        ]

    def clean(self):
        if self.correct_answer and self.options and self.correct_answer not in self.options:
            raise ValidationError("correct_answer must be one of options")

    @property
    def is_locked(self) -> bool:
        # Locks with its parent game
        return self.game.is_locked
    
    def save(self, *args, **kwargs):
        # Keep denorms synced from parent game BEFORE saving
        if self.game_id:
            self.season = self.game.season
            self.week = self.game.week

        # Detect answer change BEFORE save
        answer_before = None
        if self.pk:
            answer_before = (
                type(self).objects.only("correct_answer").filter(pk=self.pk)
                .values_list("correct_answer", flat=True).first()
            )

        with transaction.atomic():
            super().save(*args, **kwargs)

            # Cascade grading only if the answer changed
            if answer_before != self.correct_answer:
                from predictions.models import PropBetPrediction
                if self.correct_answer:
                    PropBetPrediction.objects.filter(prop_bet=self).update(
                        is_correct=Case(
                            When(answer=self.correct_answer, then=Value(True)),
                            default=Value(False),
                            output_field=BooleanField(),
                        )
                    )
                else:
                    PropBetPrediction.objects.filter(prop_bet=self).update(is_correct=None)

    def __str__(self):
        return f"S{self.season} W{self.week} ({self.category}): {self.question}"

class Window(models.Model):
    season = models.PositiveSmallIntegerField(db_index=True)
    date = models.DateField(db_index=True)
    slot = models.CharField(max_length=10, choices=WINDOW_SLOTS, db_index=True)

    is_complete = models.BooleanField(default=False, db_index=True)
    games_total = models.PositiveSmallIntegerField(default=0)
    props_total = models.PositiveSmallIntegerField(default=0)
    games_completed = models.PositiveSmallIntegerField(default=0)
    props_completed = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["season", "date", "slot"], name="uq_window_season_date_slot"),
        ]
        indexes = [
            models.Index(fields=["season", "date", "slot"], name="ix_window_order"),
            models.Index(fields=["season", "is_complete", "date"], name="ix_window_complete"),
        ]

    @property
    def key(self) -> str:
        return f"{self.date.isoformat()}:{self.slot}"

    @property
    def slot_code(self) -> int:
        return SLOT_ORDER[self.slot]

    def previous(self):
        slot_case = Case(
            When(slot="morning", then=Value(0)),
            When(slot="afternoon", then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
        cur_code = self.slot_code
        return (
            Window.objects.filter(season=self.season)
            .annotate(_code=slot_case)
            .filter(Q(date__lt=self.date) | Q(date=self.date, _code__lt=cur_code))
            .order_by("-date", "-_code")
            .first()
        )
    
    def __str__(self):
        return f"{self.date}:{self.slot} | {self.games_completed}/{self.games_total} games | {self.props_completed}/{self.props_total} props"