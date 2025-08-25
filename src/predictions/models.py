from django.db import models
from django.conf import settings
from games.models import Game
import inspect

class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    predicted_winner = models.CharField(max_length=50, default="N/A")
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Money-line prediction"
        verbose_name_plural = "Money-line predictions"
        unique_together = ('user', 'game')
        indexes = [
            models.Index(fields=["user", "is_correct"]),
            models.Index(fields=["game", "is_correct"]),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to correctness even when locked
        if self.pk:
            old = Prediction.objects.get(pk=self.pk)
            updating_correctness_only = (
                self.predicted_winner == old.predicted_winner and
                self.game == old.game and
                self.user == old.user
            )
        else:
            updating_correctness_only = False

        if self.game.is_locked and not updating_correctness_only:
            # Allow saving from admin
            if not any('django/contrib/admin' in frame.filename for frame in inspect.stack()):
                raise ValueError("This game is locked. Predictions cannot be changed.")

        if self.predicted_winner not in [self.game.home_team, self.game.away_team]:
            raise ValueError("Invalid prediction: Team not in this game")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.game.winner is not None:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - Week {self.game.week}: {self.predicted_winner} ({status})"
        return f"{self.user.username} - Week {self.game.week}: {self.predicted_winner}"


class PropBet(models.Model):
    CATEGORY_CHOICES = [
        ('over_under', 'Over/Under'),
        ('point_spread', 'Point Spread'),
        ('take_the_bait', 'Take-the-Bait')
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="prop_bets")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=list)
    correct_answer = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.correct_answer:
            for prediction in self.propbetprediction_set.all():
                prediction.is_correct = (prediction.answer == self.correct_answer)
                prediction.save()

    def __str__(self):
        return f"Week {self.game.week} ({self.category}): {self.question}"


class PropBetPrediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prop_bet = models.ForeignKey(PropBet, on_delete=models.CASCADE)
    answer = models.CharField(max_length=50)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'prop_bet')
        indexes = [
            models.Index(fields=["user", "is_correct"]),
            models.Index(fields=["prop_bet", "is_correct"]),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to correctness even when locked
        if self.pk:
            old = PropBetPrediction.objects.get(pk=self.pk)
            updating_correctness_only = (
                self.user == old.user and
                self.prop_bet == old.prop_bet and
                self.answer == old.answer
            )
        else:
            updating_correctness_only = False

        if hasattr(self, 'prop_bet') and hasattr(self.prop_bet, 'game') \
           and self.prop_bet.game.is_locked and not updating_correctness_only:
            if not any('django/contrib/admin' in frame.filename for frame in inspect.stack()):
                raise ValueError("This prop bet is locked. You cannot change your prediction.")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.prop_bet.correct_answer:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - {self.prop_bet.question} ({status})"
        return f"{self.user.username} - {self.prop_bet.question}"


# NOTE: Keeping these small tables for audit/frozen weekly views only
class WeeklySnapshot(models.Model):
    """Deprecated as a source of truth. (Kept only for back-compat reads.)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    week = models.IntegerField()
    weekly_points = models.IntegerField(default=0)
    weekly_game_correct = models.IntegerField(default=0)
    weekly_game_total = models.IntegerField(default=0)
    weekly_prop_correct = models.IntegerField(default=0)
    weekly_prop_total = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    total_game_correct = models.IntegerField(default=0)
    total_game_total = models.IntegerField(default=0)
    total_prop_correct = models.IntegerField(default=0)
    total_prop_total = models.IntegerField(default=0)
    rank = models.IntegerField()
    total_users = models.IntegerField()
    points_from_leader = models.IntegerField(default=0)
    weekly_accuracy = models.FloatField(null=True, blank=True)
    overall_accuracy = models.FloatField(null=True, blank=True)
    moneyline_accuracy = models.FloatField(null=True, blank=True)
    prop_accuracy = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'week')
        ordering = ['week', 'rank']

    def __str__(self):
        return f"{self.user.username} - Week {self.week} (#{self.rank})"


class RankHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    week = models.IntegerField()
    rank = models.IntegerField()
    previous_rank = models.IntegerField(null=True, blank=True)
    rank_change = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'week')
        ordering = ['week', 'rank']

    @property
    def trend_direction(self):
        if self.rank_change > 0:
            return 'up'
        elif self.rank_change < 0:
            return 'down'
        else:
            return 'same'

    @property
    def rank_change_display(self):
        if self.rank_change > 0:
            return f"+{self.rank_change}"
        elif self.rank_change < 0:
            return str(self.rank_change)
        else:
            return "—"

    def __str__(self):
        return f"{self.user.username} - Week {self.week}: #{self.rank} ({self.rank_change_display})"


class UserStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    streak_type = models.CharField(
        max_length=10,
        choices=[('win', 'Win'), ('loss', 'Loss')],
        default='win'
    )
    longest_win_streak = models.IntegerField(default=0)
    longest_loss_streak = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.current_streak} {self.streak_type} streak"


class LeaderboardSnapshot(models.Model):
    week = models.IntegerField()
    snapshot_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('week',)

    def __str__(self):
        return f"Leaderboard - Week {self.week}"


class SeasonStats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    best_week_points = models.IntegerField(default=0)
    best_week_number = models.IntegerField(null=True, blank=True)
    highest_rank = models.IntegerField(null=True, blank=True)
    highest_rank_week = models.IntegerField(null=True, blank=True)
    weeks_in_top_3 = models.IntegerField(default=0)
    weeks_in_top_5 = models.IntegerField(default=0)
    weeks_as_leader = models.IntegerField(default=0)
    favorite_team_picked = models.CharField(max_length=50, blank=True)
    favorite_team_pick_count = models.IntegerField(default=0)
    most_successful_category = models.CharField(max_length=20, blank=True)
    trending_direction = models.CharField(
        max_length=10,
        choices=[('up', 'Trending Up'), ('down', 'Trending Down'), ('stable', 'Stable')],
        default='stable'
    )
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Season Stats"