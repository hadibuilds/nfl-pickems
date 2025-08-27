# games/admin.py
from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Game

# Optional imports for the correction + snapshot republish action
try:
    from predictions.models import CorrectionEvent
    from predictions.services.snapshots import publish_after_snapshot
    HAVE_CORRECTIONS = True
except Exception:
    # If predictions app pieces aren't wired yet, we still want the admin to load.
    HAVE_CORRECTIONS = False

PLACEHOLDER = "— Not Final —"
class GameAdminForm(forms.ModelForm):
    """
    Renders 'winner' as a dropdown with:
      - "— Not Final —" (blank)
      - home_team
      - away_team
    Validates that a set winner must match one of those teams.
    """
    class Meta:
        model = Game
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        game = self.instance if getattr(self.instance, "pk", None) else None

        # Build winner choices dynamically
        choices = [("", PLACEHOLDER)]
        home = getattr(game, "home_team", "") if game else ""
        away = getattr(game, "away_team", "") if game else ""
        if home:
            choices.append((home, home))
        if away:
            choices.append((away, away))

        # Attach select widget
        if "winner" in self.fields:
            self.fields["winner"].required = False
            self.fields["winner"].widget = forms.Select(choices=choices)
            # UX hints if teams not set yet
            if not home or not away:
                self.fields["winner"].help_text = (
                    "Select home/away teams first. Save the game, then choose a winner."
                )

        # Small hint for window_key if present in your model
        if "window_key" in self.fields:
            field = self.fields["window_key"]
            field.disabled = True  # managed by signals/ingest; don’t hand-edit
            if not getattr(game, "window_key", None):
                field.help_text = (
                    "Derived from start_time in America/Los_Angeles (YYYY-MM-DD:morning|afternoon|late)."
                )

    def clean_winner(self):
        """
        Ensure winner is either blank (not final) or exactly the home/away team text.
        Convert empty selection to None so your model logic treats it as 'not final'.
        """
        winner = self.cleaned_data.get("winner") or None  # "" -> None
        game = self.instance

        # If a winner is provided, it must match one of the teams
        if winner and game:
            if winner not in {game.home_team, game.away_team}:
                raise ValidationError("Winner must be the home or away team for this game.")
        return winner


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm

    # Show useful columns; include window_key if present on your model
    list_display = (
        "id",
        "week",
        "start_time",
        "home_team",
        "away_team",
        "winner",
        "locked",
        "window_key",
    )
    list_filter = ("week", "locked", "window_key")
    search_fields = ("home_team", "away_team", "window_key")

    # ---------------------------
    # Historical correction action
    # ---------------------------
    actions = ["apply_historical_correction"]

    def apply_historical_correction(self, request, queryset):
        """
        Groups selected games by window_key, records a CorrectionEvent per window,
        and republishes the AFTER snapshot idempotently.
        """
        if not HAVE_CORRECTIONS:
            self.message_user(
                request,
                "Corrections system is not available yet (predictions app pieces missing).",
                level=messages.WARNING,
            )
            return

        # Partition selected games by window_key
        by_wk = {}
        for g in queryset:
            wk = getattr(g, "window_key", None)
            if not wk:
                continue
            by_wk.setdefault(wk, []).append(g)

        if not by_wk:
            self.message_user(
                request,
                "No valid window_key found for the selected games.",
                level=messages.WARNING,
            )
            return

        # Create events and republish per window
        total_published = 0
        for wk, games in by_wk.items():
            game_ids = [g.id for g in games]
            ce = CorrectionEvent.objects.create(
                window_key=wk,
                affected_game_ids=game_ids,
                changes=[],  # you can populate detailed diffs elsewhere if you capture them
                reason="Admin correction via Game list action",
                actor=getattr(request, "user", None),
            )
            snap, created = publish_after_snapshot(wk, correction_event=ce)
            if created:
                total_published += 1
                self.message_user(
                    request,
                    f"[{wk}] Published AFTER snapshot v{snap.version}.",
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    f"[{wk}] No change detected; snapshot not updated.",
                    level=messages.INFO,
                )

        if total_published == 0:
            self.message_user(
                request,
                "Historical correction applied; no AFTER snapshots needed updating.",
                level=messages.INFO,
            )
    apply_historical_correction.short_description = (
        "Apply Historical Correction → republish AFTER snapshot"
    )
