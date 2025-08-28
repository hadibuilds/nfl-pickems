from django.contrib import admin
from .models import Game, PropBet

class PropBetInline(admin.TabularInline):
    model = PropBet
    extra = 0
    fields = ("category", "question", "correct_answer")
    show_change_link = True

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("week", "home_team", "away_team", "start_time", "locked", "is_locked_display", "winner")
    list_filter = ("week", "locked")
    search_fields = ("home_team", "away_team")
    actions = ["unlock_games"]
    inlines = [PropBetInline]

    def is_locked_display(self, obj):
        return obj.is_locked
    is_locked_display.short_description = "Currently Locked"
    is_locked_display.boolean = True

    def unlock_games(self, request, queryset):
        queryset.update(locked=False)
        self.message_user(request, "Selected games have been unlocked.")
    unlock_games.short_description = "Unlock selected games (manual override)"

@admin.register(PropBet)
class PropBetAdmin(admin.ModelAdmin):
    list_display = ("get_week", "game", "category", "question", "correct_answer")
    list_filter = ("category", "game__week")
    search_fields = ("question",)
    ordering = ("game__week",)

    def get_week(self, obj):
        return obj.game.week
    get_week.short_description = "Week"
    get_week.admin_order_field = "game__week"

