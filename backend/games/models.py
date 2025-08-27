from django.db import models
from django.utils import timezone

class Game(models.Model):
    week = models.IntegerField()
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    start_time = models.DateTimeField()
    locked = models.BooleanField(default=False)  # Manual override
    winner = models.CharField(max_length=50, null=True, blank=True)
    window_key = models.CharField(max_length=64, db_index=True, blank=True, null=True)

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
