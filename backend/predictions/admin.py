# predictions/admin.py
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.conf import settings
from django import forms

from .models import Prediction, PropBetPrediction

from analytics.models import UserStatHistory, UserSeasonTotals
from games.models import Game, PropBet



# Try to import Game so we can show it under "Non-User Data"
try:
    from games.models import Game
    HAS_GAME = True
except Exception:
    HAS_GAME = False


# ===========================
#   ModelAdmin definitions
# ===========================

class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "predicted_winner", "is_correct")
    list_filter = ("is_correct", "game__week")
    search_fields = ("user__username", "game__home_team", "game__away_team", "predicted_winner")
    ordering = ("-game__week", "-game__start_time")
class PropBetPredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "prop_bet", "answer", "is_correct")
    list_filter = ("is_correct", "prop_bet__category", "prop_bet__game__week")
    search_fields = ("user__username", "prop_bet__question", "answer")
    ordering = ("-prop_bet__game__week",)


# ===========================
#   Register remaining models
# ===========================

# Remove UserStreak registration and update model groupings

admin.site.register(Prediction, PredictionAdmin)
admin.site.register(PropBetPrediction, PropBetPredictionAdmin)

# Only register legacy snapshots if needed for backward compatibility
if getattr(settings, "LEGACY_SNAPSHOTS_ENABLED", False):
    admin.site.register(WeeklySnapshot, WeeklySnapshotAdmin)

# ============================================
#   Updated admin grouping - cleaner sections
# ============================================

USER_MODEL_NAMES = {"User"}
GROUP_MODEL_NAMES = {"Group"}
NONUSER_MODEL_NAMES = {"PropBet"} | ({"Game"} if HAS_GAME else set())

# UserSeasonTotals is live data that updates throughout season, so it belongs in User Data
USERDATA_MODEL_NAMES = {"Prediction", "PropBetPrediction"}

# Only TRUE immutable snapshot models
SNAPSHOT_MODEL_NAMES = {"UserStatHistory", "LeaderboardSnapshot", "UserSeasonTotals"}

# Add legacy snapshots only if enabled
if getattr(settings, "LEGACY_SNAPSHOTS_ENABLED", False):
    SNAPSHOT_MODEL_NAMES.add("WeeklySnapshot")

# Save the *original class method* so we can call it safely
_ORIG_CLASS_GET_APP_LIST = admin.AdminSite.get_app_list

def _custom_get_app_list(adminsite, request):
    """
    Build a custom app list with five ordered pseudo sections first:
      Users → Groups → Non-User Data → User Data → Snapshot Data
    Then append all remaining apps/models as Django would normally display.
    """
    # Call Django's original class method (not super()), then reshape
    apps = list(_ORIG_CLASS_GET_APP_LIST(adminsite, request))

    # Flatten all models (keep original dict structure for each model row)
    flat = []
    for app in apps:
        for m in app["models"]:
            flat.append({
                "app_label": app["app_label"],
                "app_name": app["name"],
                "app_url": app["app_url"],
                "model": m,
            })

    def pluck(names, pool):
        picked, rest = [], []
        ns = set(names)
        for row in pool:
            if row["model"]["object_name"] in ns:
                picked.append(row)
            else:
                rest.append(row)
        return picked, rest

    # Build the five sections in exact order
    users_rows, rest = pluck(USER_MODEL_NAMES, flat)
    groups_rows, rest = pluck(GROUP_MODEL_NAMES, rest)
    nonuser_rows, rest = pluck(NONUSER_MODEL_NAMES, rest)
    userdata_rows, rest = pluck(USERDATA_MODEL_NAMES, rest)
    snapshot_rows, rest = pluck(SNAPSHOT_MODEL_NAMES, rest)

    def make_app(name, rows, label):
        return {
            "name": name,
            "app_label": label,
            "app_url": "",
            "has_module_perms": True,
            "models": sorted([r["model"] for r in rows], key=lambda m: m["name"].lower()),
        }

    pseudo = []
    if users_rows:    pseudo.append(make_app("Users", users_rows, "z_users"))
    if groups_rows:   pseudo.append(make_app("Groups", groups_rows, "z_groups"))
    if nonuser_rows:  pseudo.append(make_app("Non-User Data", nonuser_rows, "z_nonuser"))
    if userdata_rows: pseudo.append(make_app("User Data", userdata_rows, "z_user"))
    if snapshot_rows: pseudo.append(make_app("Snapshot Data", snapshot_rows, "z_snapshot"))

    # Rebuild remaining real apps (auth, admin, etc.)
    by_app = {}
    for row in rest:
        key = (row["app_label"], row["app_name"], row["app_url"])
        by_app.setdefault(key, []).append(row["model"])

    remaining = []
    for (app_label, app_name, app_url), models in by_app.items():
        remaining.append({
            "name": app_name,
            "app_label": app_label,
            "app_url": app_url,
            "has_module_perms": True,
            "models": sorted(models, key=lambda m: m["name"].lower()),
        })

    # Our five pseudo sections FIRST, then the rest alphabetically by app name
    return pseudo + sorted(remaining, key=lambda a: a["name"].lower())

# Patch the AdminSite *class* so all admin sites use this ordering
admin.AdminSite.get_app_list = _custom_get_app_list

# Optional: header branding
admin.site.site_header = "NFL Pickems Admin"
admin.site.site_title = "NFL Pickems Admin"
admin.site.index_title = "Dashboard & Statistics Management"