# predictions/signals.py
"""
Grade user predictions when results are saved:
- Game.winner -> Prediction.is_correct
- PropBet.correct_answer -> PropBetPrediction.is_correct
"""

from django.db import transaction
from django.db.models import BooleanField, Case, Value, When
from django.db.models.signals import post_save
from django.dispatch import receiver

from games.models import Game, PropBet
from .models import Prediction, PropBetPrediction


@receiver(post_save, sender=Game)
def grade_moneyline_predictions(sender, instance: Game, **kwargs):
    """Re-evaluate all moneyline predictions when a game's winner changes."""
    winner = getattr(instance, "winner", None)

    def do_update():
        if not winner:
            # Clear correctness if result is cleared/unknown
            Prediction.objects.filter(game=instance).update(is_correct=None)
            return

        Prediction.objects.filter(game=instance).update(
            is_correct=Case(
                When(predicted_winner=winner, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    transaction.on_commit(do_update)


@receiver(post_save, sender=PropBet)
def grade_prop_predictions(sender, instance: PropBet, **kwargs):
    """Re-evaluate all prop-bet predictions when the prop's correct answer changes."""
    correct = getattr(instance, "correct_answer", None)

    def do_update():
        if not correct:
            PropBetPrediction.objects.filter(prop_bet=instance).update(is_correct=None)
            return

        # Your model uses 'answer' (from the uploads) — compare that to correct_answer
        PropBetPrediction.objects.filter(prop_bet=instance).update(
            is_correct=Case(
                When(answer=correct, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    transaction.on_commit(do_update)
