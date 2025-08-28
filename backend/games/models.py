from django.db import models
from django.utils import timezone


class Game(models.Model):
    week = models.IntegerField()
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    start_time = models.DateTimeField()
    locked = models.BooleanField(default=False)  # Manual override
    winner = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ('week', 'home_team', 'away_team')

    @property
    def is_locked(self):
        """Dynamically locked if time has passed OR manually locked."""
        return self.locked or timezone.now() >= self.start_time

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        from predictions.models import Prediction
        predictions = Prediction.objects.filter(game=self)

        if self.winner:
            # Set correctness based on winner
            for p in predictions:
                p.is_correct = (p.predicted_winner == self.winner)
                p.save()
        else:
            # Reset correctness if winner is cleared
            for p in predictions:
                p.is_correct = None
                p.save()

    def __str__(self):
        status = "🔒" if self.is_locked else ""
        return f"Week {self.week}: {self.away_team} @ {self.home_team} {status}"

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