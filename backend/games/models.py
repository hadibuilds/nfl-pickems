from django.db import models
from django.utils import timezone
try:
    from zoneinfo import ZoneInfo  # Django 4+/Py3.9+
    PT_TZ = ZoneInfo("America/Los_Angeles")
except Exception:                  # older envs fallback
    import pytz
    PT_TZ = pytz.timezone("America/Los_Angeles")
class Game(models.Model):
    season = models.IntegerField(db_index=True, null=True, blank=True)
    week = models.IntegerField()
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    start_time = models.DateTimeField()
    locked = models.BooleanField(default=False)
    winner = models.CharField(max_length=50, null=True, blank=True)

    # Window key like "YYYY-MM-DD:morning|afternoon|late" (Pacific-time windowing)
    window_key = models.CharField(max_length=64, db_index=True, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("season", "week", "home_team", "away_team"),
                name="uniq_game_per_season_week_matchup",
            ),
        ]
        indexes = [
            models.Index(fields=["season", "week"], name="game_season_week_idx"),
            models.Index(fields=["season", "window_key"], name="game_season_window_idx"),
            models.Index(fields=["season", "start_time"], name="game_season_start_idx"),
        ]
        ordering = ["season", "week", "start_time"]
    
    @property
    def is_locked(self) -> bool:
        """
        Dynamically locked if time has passed OR manually locked.
        Uses tz-aware compare; start_time should be UTC in DB.
        """
        now = timezone.now()
        start = self.start_time
        if timezone.is_naive(start):
            start = timezone.make_aware(start, timezone.utc)
        return bool(self.locked or now >= start)

    @property
    def start_time_pt(self):
        """Kickoff localized to America/Los_Angeles (for admin/UI)."""
        start = self.start_time
        if timezone.is_naive(start):
            start = timezone.make_aware(start, timezone.utc)
        return start.astimezone(PT_TZ)

    @property
    def window_slot(self) -> str:
        """
        morning  : < 13:00 PT
        afternoon: 13:00–16:59 PT
        late     : >= 17:00 PT
        """
        h = self.start_time_pt.hour
        if h < 13:
            return "morning"
        elif h < 17:
            return "afternoon"
        return "late"

    # --- PropBet resolution helpers (linked via related_name="prop_bets") ---

    @property
    def prop_bets_total(self) -> int:
        return self.prop_bets.count()

    @property
    def prop_bets_unresolved_count(self) -> int:
        return self.prop_bets.filter(correct_answer__isnull=True).count()

    @property
    def prop_bets_resolved_count(self) -> int:
        total = self.prop_bets_total
        return total - self.prop_bets_unresolved_count

    @property
    def all_prop_bets_resolved(self) -> bool:
        return self.prop_bets_unresolved_count == 0

    @property
    def is_fully_resolved(self) -> bool:
        """
        True when the game winner is set AND all linked PropBets are resolved.
        Handy for window completeness checks or admin badges.
        """
        return bool(self.winner) and self.all_prop_bets_resolved

    def __str__(self):
        lock_glyph = "🔒" if self.is_locked else ""
        wk = f"Week {self.week}" if getattr(self, "week", None) is not None else str(self.season or "")
        return f"{wk}: {self.away_team} @ {self.home_team} {lock_glyph}"
    
    def __str__(self):
        s = self.season if self.season is not None else "??"
        status = "🔒" if self.is_locked else ""
        return f"{status} {self.away_team} @ {self.home_team} (W{self.week}:{s})"


class PropBet(models.Model):
    """
    Each PropBet is *owned* by a Game. Season and window_key are
    denormalized for fast filtering and are auto-synced from Game via signals.
    """
    CATEGORY_CHOICES = [
        ("over_under", "Over/Under"),
        ("point_spread", "Point Spread"),
        ("take_the_bait", "Take-the-Bait"),
    ]

    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="prop_bets",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)

    # Flexible representation for UI (list of strings or list of dicts)
    options = models.JSONField(default=list)

    correct_answer = models.CharField(max_length=50, blank=True, null=True)

    # ⤵ Denormalized attributes (copied from Game). Indexed for windowed queries.
    season = models.IntegerField(db_index=True, blank=True, null=True)
    window_key = models.CharField(max_length=64, db_index=True, blank=True, null=True)

    class Meta:
        # Avoid duplicate questions on the same game
        constraints = [
            models.UniqueConstraint(
                fields=("game", "question"),
                name="uniq_propbet_per_game_question",
            ),
        ]
        indexes = [
            models.Index(fields=["season", "window_key"], name="propbet_season_window_idx"),
            models.Index(fields=["game", "season"], name="propbet_game_season_idx"),
        ]

    def __str__(self):
        return f"[{self.category}] {self.question}"
