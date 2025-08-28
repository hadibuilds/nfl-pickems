# games/signals.py
"""
Keep PropBet.season/window_key in sync with its owning Game.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Game, PropBet


@receiver(pre_save, sender=PropBet)
def sync_propbet_denorms_before_save(sender, instance: PropBet, **kwargs):
    game = instance.game
    if game:
        if getattr(instance, "season", None) != getattr(game, "season", None):
            instance.season = getattr(game, "season", None)
        if getattr(instance, "window_key", None) != getattr(game, "window_key", None):
            instance.window_key = getattr(game, "window_key", None)


@receiver(post_save, sender=Game)
def cascade_game_denorms_to_props(sender, instance: Game, **kwargs):
    # Bulk update only props that are out of sync
    PropBet.objects.filter(game=instance).exclude(
        season=instance.season, window_key=instance.window_key
    ).update(season=instance.season, window_key=instance.window_key)
