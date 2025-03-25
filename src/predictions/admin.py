from django.contrib import admin
from .models import Prediction, PropBet, PropBetPrediction

# ✅ Admin for game predictions (money-line picks)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'predicted_winner', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('user__username', 'game__home_team', 'game__away_team', 'predicted_winner')


# ✅ Admin for prop bets
class PropBetAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'game', 'category', 'question', 'correct_answer')
    ordering = ('game__week',)
    search_fields = ('question',)
    list_filter = ('category',)

    def get_week(self, obj):
        return obj.game.week
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'game__week'


# ✅ Admin for user prop bet predictions
class PropBetPredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'prop_bet', 'answer', 'is_correct')
    list_filter = ('is_correct', 'prop_bet__category')
    search_fields = ('user__username', 'prop_bet__question', 'answer')


# Register all models
admin.site.register(Prediction, PredictionAdmin)
admin.site.register(PropBet, PropBetAdmin)
admin.site.register(PropBetPrediction, PropBetPredictionAdmin)
