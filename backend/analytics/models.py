# analytics/models.py
from __future__ import annotations
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserWindowStat(models.Model):
    window = models.ForeignKey("games.Window", on_delete=models.CASCADE, related_name="user_stats")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="window_stats")
    ml_correct = models.IntegerField(default=0)
    pb_correct = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    rank_dense = models.IntegerField(default=0)

    # audit
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["window", "user"], name="uniq_user_window_stat"),
        ]
        indexes = [
            # Just a normal index; ORDER BY variant is optional optimization
            models.Index(fields=["window"]),
            models.Index(fields=["user", "window"]),
        ]
    ordering = ["window_id", "rank_dense", "-total_points"]

    def __str__(self):
        return f"{self.window} • {self.user} • pts={self.total_points} • r={self.rank_dense}"
