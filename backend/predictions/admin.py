# predictions/admin.py
from django.contrib import admin
from .models import MoneyLinePrediction, PropBetPrediction

@admin.register(MoneyLinePrediction)
class MoneyLinePredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "predicted_winner", "is_correct")
    list_filter = ("is_correct", "game__season", "game__week")
    search_fields = ("user__username", "predicted_winner")

@admin.register(PropBetPrediction)
class PropBetPredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "prop_bet", "answer", "is_correct")
    list_filter = ("is_correct", "prop_bet__game__season", "prop_bet__game__week")
    search_fields = ("user__username", "answer")
