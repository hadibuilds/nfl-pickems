# analytics/admin.py
from django.contrib import admin
from .models import UserWindowStat

@admin.register(UserWindowStat)
class UserWindowStatAdmin(admin.ModelAdmin):
    list_display = ("window", "user", "ml_correct", "pb_correct", "total_points", "rank_dense", "computed_at")
    list_filter = ("window__season", "window__slot")
    search_fields = ("user__username",)
