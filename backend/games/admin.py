from django.contrib import admin
from .models import Game

class GameAdmin(admin.ModelAdmin):
    list_display = ('week', 'home_team', 'away_team', 'start_time', 'locked', 'is_locked_display', 'winner')
    list_filter = ('week', 'locked')
    search_fields = ('home_team', 'away_team')
    actions = ['unlock_games']

    def is_locked_display(self, obj):
        return obj.is_locked
    is_locked_display.short_description = 'Currently Locked'
    is_locked_display.boolean = True  # ✅ Adds ✅/❌ icons in admin UI

    def unlock_games(self, request, queryset):
        """Admin action to unlock games (manual override)"""
        queryset.update(locked=False)
        self.message_user(request, "Selected games have been unlocked.")

    unlock_games.short_description = "Unlock selected games (manual override)"

admin.site.register(Game, GameAdmin)

