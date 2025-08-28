# backend/predictions/models.py

from django.db import models
from django.conf import settings
from games.models import Game, PropBet
import inspect

class Prediction(models.Model):
    """
    Money-line prediction for a game (user-entered data).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moneyline_predictions")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moneyline_predictions")
    predicted_winner = models.CharField(max_length=50, default="N/A")
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "Money-line prediction"
        verbose_name_plural = "Money-line predictions"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "game"),
                name="uniq_moneyline_prediction_per_user_game",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_correct"], name="pred_user_correct_idx"),
            models.Index(fields=["game", "is_correct"], name="pred_game_correct_idx"),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to 'is_correct' even when the game is locked
        updating_correctness_only = False
        if self.pk:
            old = type(self).objects.only("user", "game", "predicted_winner", "is_correct").get(pk=self.pk)
            updating_correctness_only = (
                self.user_id == old.user_id and
                self.game_id == old.game_id and
                self.predicted_winner == old.predicted_winner and
                self.is_correct != old.is_correct
            )

        # Respect game lock (games.Game uses `locked`, not `is_locked`)
        if getattr(self.game, "locked", False) and not updating_correctness_only:
            # Allow saves coming from Django admin
            if not any("django/contrib/admin" in f.filename for f in inspect.stack()):
                raise ValueError("This game is locked. Predictions cannot be changed.")

        # Validate the pick (allow "N/A" placeholder)
        if self.predicted_winner not in (self.game.home_team, self.game.away_team, "N/A"):
            raise ValueError("Invalid prediction: Team not in this game")

        super().save(*args, **kwargs)

    def __str__(self):
        pick = self.predicted_winner or "N/A"
        if self.game.winner is not None and self.is_correct is not None:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - Week {self.game.week}: {pick} ({status})"
        return f"{self.user.username} - Week {self.game.week}: {pick}"


class PropBetPrediction(models.Model):
    """
    User's prediction for a specific PropBet (owned by games.PropBet).
    Denormalized season/window_key are synced from the owning PropBet for fast filtering.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="propbet_predictions")
    prop_bet = models.ForeignKey(PropBet, on_delete=models.CASCADE, related_name="predictions")
    answer = models.CharField(max_length=50)
    is_correct = models.BooleanField(null=True, blank=True)

    # Denorms to speed up window/season queries without joins
    season = models.IntegerField(db_index=True, blank=True, null=True)
    window_key = models.CharField(max_length=64, db_index=True, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "prop_bet"),
                name="uniq_propbet_prediction_per_user_prop",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_correct"], name="pbpred_user_correct_idx"),
            models.Index(fields=["prop_bet", "is_correct"], name="pbpred_prop_correct_idx"),
            models.Index(fields=["season", "window_key"], name="pbpred_season_window_idx"),
        ]

    def save(self, *args, **kwargs):
        # Allow updates to 'is_correct' even when the game's locked
        updating_correctness_only = False
        if self.pk:
            old = type(self).objects.only("user", "prop_bet", "answer", "is_correct").get(pk=self.pk)
            updating_correctness_only = (
                self.user_id == old.user_id and
                self.prop_bet_id == old.prop_bet_id and
                self.answer == old.answer and
                self.is_correct != old.is_correct
            )

        # Respect lock via the owning game
        game_locked = False
        pb = getattr(self, "prop_bet", None)
        if pb and isinstance(pb, PropBet):
            game_locked = getattr(pb.game, "locked", False)
        else:
            try:
                pb = PropBet.objects.select_related("game").only("id", "game__locked").get(pk=self.prop_bet_id)
                game_locked = getattr(pb.game, "locked", False)
            except PropBet.DoesNotExist:
                pass

        if game_locked and not updating_correctness_only:
            if not any("django/contrib/admin" in f.filename for f in inspect.stack()):
                raise ValueError("This prop bet is locked. You cannot change your prediction.")

        # Keep denorms in sync from the PropBet (and therefore from the Game)
        if pb and isinstance(pb, PropBet):
            self.season = pb.season
            self.window_key = pb.window_key
        elif self.prop_bet_id:
            try:
                pb = PropBet.objects.only("season", "window_key").get(pk=self.prop_bet_id)
                self.season = pb.season
                self.window_key = pb.window_key
            except PropBet.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        q = getattr(self.prop_bet, "question", f"PropBet {self.prop_bet_id}")
        if getattr(self.prop_bet, "correct_answer", None) is not None and self.is_correct is not None:
            status = "✅" if self.is_correct else "❌"
            return f"{self.user.username} - {q} ({status})"
        return f"{self.user.username} - {q}"

class CorrectionEvent(models.Model):
    """
    Append-only audit record for historical corrections that impact a window.
    Example changes payload:
      [
        {"type": "game", "id": 123, "field": "winner", "old": "SEA", "new": "LAR"},
        {"type": "prop", "id": 456, "field": "correct_answer", "old": "Over", "new": "Under"}
      ]
    """
    window_key = models.CharField(max_length=64, db_index=True)
    affected_game_ids = models.JSONField(default=list, blank=True)  # portable (ArrayField if you prefer PG-only)
    changes = models.JSONField(default=list, blank=True)            # list of {type,id,field,old,new}
    reason = models.CharField(max_length=255, blank=True, default="")
    actor = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True, blank=True, on_delete=models.SET_NULL, related_name="correction_events"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"CorrectionEvent({self.window_key} @ {self.created_at:%Y-%m-%d %H:%M:%S})"