# backend/games/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Case, When, Value, BooleanField  # <- use ORM, not admin.models

from .models import Game, PropBet, Window


# --- helpers ---------------------------------------------------------------

def _related_query_name(model_cls, related_model_name: str, fallback: str) -> str:
    """
    Return the reverse related *query* name from model_cls to a related model
    (e.g., Game <- Prediction). Works with or without explicit related_name.
    """
    for f in model_cls._meta.get_fields():
        if getattr(f, "is_relation", False) and getattr(f, "auto_created", False) and not getattr(f, "concrete", True):
            rel = getattr(f, "related_model", None)
            if rel is not None and rel.__name__ == related_model_name:
                # Django 5 exposes get_related_query_name(); fall back to attrs if needed
                if hasattr(f, "get_related_query_name"):
                    return f.get_related_query_name()
                rqn = getattr(f, "related_query_name", None)
                if rqn:
                    return rqn
                rn = getattr(f, "related_name", None)
                if rn:
                    # related_name (accessor) is not the query name, but Count() can still use it
                    return rn
                # f.name is typically the base (e.g., "prediction"), which works for Count()
                return f.name
    return fallback


# Resolve reverse query names safely (works with/without explicit related_name)
_PREDICTION_RQN = _related_query_name(Game, "Prediction", "prediction")
_PB_PREDICTION_RQN = _related_query_name(PropBet, "PropBetPrediction", "propbetprediction")


# -----------------
# Inlines
# -----------------
class PropBetInline(admin.TabularInline):
    model = PropBet
    extra = 0
    fields = ("category", "question", "options", "correct_answer", "is_locked_display")
    readonly_fields = ("is_locked_display",)
    show_change_link = True

    def is_locked_display(self, obj):
        return "🔒" if obj and obj.is_locked else "—"
    is_locked_display.short_description = "Locked?"


# -----------------
# Actions
# -----------------
@admin.action(description="Recompute money-line correctness for selected games (uses current winner)")
def recompute_moneyline_correctness(modeladmin, request, queryset):
    from predictions.models import Prediction  # adapt if/when you rename

    # 1) reset where winner is NULL
    null_winner_ids = list(queryset.filter(winner__isnull=True).values_list("id", flat=True))
    if null_winner_ids:
        Prediction.objects.filter(game_id__in=null_winner_ids).update(is_correct=None)

    # 2) set correctness where winner is chosen
    for game_id, winner in queryset.exclude(winner__isnull=True).values_list("id", "winner"):
        Prediction.objects.filter(game_id=game_id).update(
            is_correct=Case(
                When(predicted_winner=winner, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )


@admin.action(description="Clear winner on selected games (and reset money-line correctness)")
def clear_winner(modeladmin, request, queryset):
    from predictions.models import Prediction
    updated = queryset.update(winner=None)
    if updated:
        Prediction.objects.filter(game__in=queryset).update(is_correct=None)


# -----------------
# ModelAdmins
# -----------------
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    date_hierarchy = "start_time"
    inlines = [PropBetInline]

    list_display = (
        "season",
        "week",
        "matchup",
        "start_time",
        "is_locked_display",
        "winner",
        "predictions_count",
        "propbets_count",
        "window",
    )
    list_filter = ("season", "week", "winner", "locked")
    search_fields = ("home_team", "away_team")
    ordering = ("season", "week", "start_time")
    readonly_fields = ("is_locked_display", "created_updated_display")

    fieldsets = (
        (None, {"fields": ("season", "week", ("home_team", "away_team"), "start_time")}),
        ("Locking", {"fields": ("locked", "is_locked_display")}),
        ("Result", {"fields": ("winner",)}),
        ("Meta", {"fields": ("created_updated_display",)}),
        ("Window", {"fields": ("window",)}),
    )

    actions = [recompute_moneyline_correctness, clear_winner]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _predictions_count=Count(_PREDICTION_RQN, distinct=True),  # robust to related_name/no-related_name
            _propbets_count=Count("prop_bets", distinct=True),         # you have related_name="prop_bets"
        )

    def matchup(self, obj: Game):
        return f"{obj.away_team} @ {obj.home_team}"

    def is_locked_display(self, obj: Game):
        return "🔒" if obj.is_locked else "—"
    is_locked_display.short_description = "Locked?"

    def predictions_count(self, obj):
        return getattr(obj, "_predictions_count", 0)
    predictions_count.short_description = "# Picks"

    def propbets_count(self, obj):
        return getattr(obj, "_propbets_count", 0)
    propbets_count.short_description = "# PropBets"

    def created_updated_display(self, obj):
        created = getattr(obj, "created_at", None)
        updated = getattr(obj, "updated_at", None)

        def fmt(dt):
            return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M") if dt else "—"

        if created or updated:
            return format_html("<div>Created: {}<br/>Updated: {}</div>", fmt(created), fmt(updated))
        return "—"
    created_updated_display.short_description = "Timestamps"


@admin.register(PropBet)
class PropBetAdmin(admin.ModelAdmin):
    list_display = (
        "season",
        "week",
        "category",
        "short_question",
        "game",
        "correct_answer",
        "is_locked_display",
        "predictions_count",
    )
    list_filter = ("season", "week", "category", "correct_answer")
    search_fields = ("question", "game__home_team", "game__away_team")
    autocomplete_fields = ("game",)
    ordering = ("season", "week", "category", "id")
    readonly_fields = ("is_locked_display",)

    actions = ["recompute_propbet_correctness"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("game").annotate(
            _predictions_count=Count(_PB_PREDICTION_RQN, distinct=True)
        )

    def short_question(self, obj):
        return (obj.question or "")[:80]
    short_question.short_description = "Question"

    def is_locked_display(self, obj: PropBet):
        return "🔒" if obj.is_locked else "—"
    is_locked_display.short_description = "Locked?"

    def predictions_count(self, obj):
        return getattr(obj, "_predictions_count", 0)
    predictions_count.short_description = "# Answers"

    @admin.action(description="Recompute prop-bet correctness for selected (uses current correct_answer)")
    def recompute_propbet_correctness(self, request, queryset):
        from predictions.models import PropBetPrediction
        for pb in queryset:
            if pb.correct_answer:
                PropBetPrediction.objects.filter(prop_bet=pb).update(
                    is_correct=Case(
                        When(answer=pb.correct_answer, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    )
                )
            else:
                PropBetPrediction.objects.filter(prop_bet=pb).update(is_correct=None)
