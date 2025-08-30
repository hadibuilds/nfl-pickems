from django import forms
from django.contrib import admin, messages
from django.db import transaction

from .models import Window, Game, PropBet
from analytics.services.window_stats import recompute_window


# ---------- Forms with safe, dynamic dropdowns ----------

class GameAdminForm(forms.ModelForm):
    """
    Winner must be either home_team or away_team (or cleared).
    We render a <select> and also validate in clean_winner.
    """
    winner = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = Game
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        home = self.instance.home_team if self.instance and self.instance.pk else (self.data.get("home_team") or self.initial.get("home_team"))
        away = self.instance.away_team if self.instance and self.instance.pk else (self.data.get("away_team") or self.initial.get("away_team"))

        choices = [("", "— Clear —")]
        if home:
            choices.append((home, home))
        if away and away != home:
            choices.append((away, away))
        self.fields["winner"].choices = choices
        self.fields["winner"].widget = forms.Select(choices=choices)

    def clean_winner(self):
        win = self.cleaned_data.get("winner")
        home = self.cleaned_data.get("home_team") or (self.instance.home_team if self.instance else None)
        away = self.cleaned_data.get("away_team") or (self.instance.away_team if self.instance else None)
        if win in ("", None):
            return None
        if win not in {home, away}:
            raise forms.ValidationError("Winner must match the home or away team.")
        return win


class PropBetAdminForm(forms.ModelForm):
    """
    Correct answer must be one of options (JSON array) or cleared.
    We render a <select> and also validate in clean_correct_answer.
    """
    correct_answer = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = PropBet
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opts = []
        # Use instance options if editing existing object
        if self.instance and getattr(self.instance, "options", None):
            if isinstance(self.instance.options, list):
                opts = self.instance.options

        # Base choices; JS will keep these in sync when options field changes
        choices = [("", "— Clear —")] + [(o, o) for o in opts]
        self.fields["correct_answer"].choices = choices
        self.fields["correct_answer"].widget = forms.Select(choices=choices)

    def clean_correct_answer(self):
        ans = self.cleaned_data.get("correct_answer")
        opts = self.cleaned_data.get("options") or []
        if ans in ("", None):
            return None
        if isinstance(opts, list) and ans not in opts:
            raise forms.ValidationError("Correct answer must be one of the defined options.")
        return ans


# ---------- Admin registrations ----------

@admin.register(Window)
class WindowAdmin(admin.ModelAdmin):
    list_display = ("season", "date", "slot", "is_complete", "completed_at", "updated_at")
    list_filter = ("season", "slot", "is_complete")
    search_fields = ("date",)
    actions = ["refresh_status"]

    @admin.action(description="Refresh status (recompute window stats)")
    def refresh_status(self, request, queryset):
        affected = {w.id for w in queryset}
        def _do():
            for wid in affected:
                recompute_window(wid)
        transaction.on_commit(_do)
        self.message_user(request, f"Scheduled recompute for {len(affected)} window(s).", messages.SUCCESS)
    
    @admin.action(description="Recompute selected window(s)")
    def recompute_selected_windows(modeladmin, request, queryset):
        for w in queryset:
            recompute_window(w.id)

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    list_display = (
        "season", "week", "home_team", "away_team", "start_time",
        "is_locked_display", "winner", "window",
    )
    list_filter = ("season", "week", "locked", "winner")
    search_fields = ("home_team", "away_team")
    actions = ["finalize_selected"]
    # IMPORTANT: Do NOT use list_editable for 'winner'—it bypasses our safe form.
    # list_editable = ("winner",)

    class Media:
        # Dynamic dropdowns (as-you-type) on the change form
        js = ("games/admin_winner_choices.js",)

    @admin.display(boolean=True, description="Locked?")
    def is_locked_display(self, obj: Game):
        return obj.is_locked

    def save_model(self, request, obj: Game, form, change):
        prev_winner = None
        prev_window_id = None
        if change:
            old = type(obj).objects.only("winner", "window_id").get(pk=obj.pk)
            prev_winner = old.winner
            prev_window_id = old.window_id

        super().save_model(request, obj, form, change)

        # Grade & recompute via finalize()
        winner_changed = (not change) or (prev_winner != obj.winner)
        window_changed = change and prev_window_id and (prev_window_id != obj.window_id)

        affected_window_ids = set()
        if winner_changed:
            obj.finalize(obj.winner)  # grades ML + recompute
            affected_window_ids.add(obj.window_id)
        if window_changed:
            affected_window_ids.add(prev_window_id)

        if affected_window_ids:
            def _do():
                for wid in affected_window_ids:
                    recompute_window(wid)
            transaction.on_commit(_do)
            self.message_user(request, "Window stats updated.", messages.SUCCESS)

    @admin.action(description="Finalize selected games (grade & recompute)")
    def finalize_selected(self, request, queryset):
        affected = set()
        for g in queryset.select_related("window"):
            with transaction.atomic():
                g.finalize(g.winner)
                affected.add(g.window_id)
        def _do():
            for wid in affected:
                recompute_window(wid)
        transaction.on_commit(_do)
        self.message_user(request, f"Finalized {len(affected)} window(s).", messages.SUCCESS)


@admin.register(PropBet)
class PropBetAdmin(admin.ModelAdmin):
    form = PropBetAdminForm
    list_display = ("game", "category", "question", "correct_answer")
    list_filter = ("category", "game__season", "game__week")
    search_fields = ("question",)
    actions = ["grade_selected"]

    class Media:
        js = ("games/admin_propbet_choices.js",)

    def save_model(self, request, obj: PropBet, form, change):
        prev_correct = None
        prev_window_id = None
        if change:
            old = type(obj).objects.select_related("game").only("correct_answer", "game__window_id").get(pk=obj.pk)
            prev_correct = old.correct_answer
            prev_window_id = old.game.window_id

        super().save_model(request, obj, form, change)

        # Only recompute when there's a meaningful scoring change
        answer_changed = (change and prev_correct != obj.correct_answer) or (not change and obj.correct_answer is not None)
        # Let games handle window moves - prop bets move automatically with their games
        window_changed = False

        affected_window_ids = set()
        if answer_changed:
            obj.grade(obj.correct_answer)  # grade + recompute
            affected_window_ids.add(obj.game.window_id)
        if window_changed:
            affected_window_ids.add(prev_window_id)

        if affected_window_ids:
            def _do():
                for wid in affected_window_ids:
                    recompute_window(wid)
            transaction.on_commit(_do)
            self.message_user(request, "Window stats updated.", messages.SUCCESS)

    @admin.action(description="Grade selected prop bets (recompute)")
    def grade_selected(self, request, queryset):
        affected = set()
        for pb in queryset.select_related("game__window"):
            with transaction.atomic():
                pb.grade(pb.correct_answer)
                affected.add(pb.game.window_id)
        def _do():
            for wid in affected:
                recompute_window(wid)
        transaction.on_commit(_do)
        self.message_user(request, f"Graded props across {len(affected)} window(s).", messages.SUCCESS)