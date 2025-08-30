# analytics/admin.py
from django.contrib import admin
from .models import UserWindowStat

@admin.register(UserWindowStat)
class UserWindowStatAdmin(admin.ModelAdmin):
    list_display = ("window", "user", "rank_dense", "rank_delta", "ml_correct", "pb_correct", "window_points", "season_cume_points", "computed_at")
    list_filter = ("window__season", "window__slot")
    search_fields = ("user__username",)
