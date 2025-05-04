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
        unique_together = ('user', 'game')

    def save(self, *args, **kwargs):
        print(f"DEBUG: predicted_winner = {self.predicted_winner}")
        print(f"DEBUG: home_team = {self.game.home_team}")
        print(f"DEBUG: away_team = {self.game.away_team}")
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
        if self.game.winner:
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

    def save(self, *args, **kwargs):
        if hasattr(self, 'prop_bet') and hasattr(self.prop_bet, 'game') and self.prop_bet.game.is_locked:
            if not any('django/contrib/admin' in frame.filename for frame in inspect.stack()):
                raise ValueError("This prop bet is locked. You cannot change your prediction.")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.prop_bet.correct_answer:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - {self.prop_bet.question} ({status})"
        return f"{self.user.username} - {self.prop_bet.question}"
