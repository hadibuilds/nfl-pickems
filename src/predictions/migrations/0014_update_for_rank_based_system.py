# predictions/migrations/0014_update_for_rank_based_system.py
from django.db import migrations

# Columns 0014 tried to re-add (already created in 0013)
USERSTAT_COLS = [
    ("week_points",              "integer NOT NULL DEFAULT 0"),
    ("week_moneyline_correct",   "integer NOT NULL DEFAULT 0"),
    ("week_moneyline_total",     "integer NOT NULL DEFAULT 0"),
    ("week_prop_correct",        "integer NOT NULL DEFAULT 0"),
    ("week_prop_total",          "integer NOT NULL DEFAULT 0"),
    ("season_moneyline_correct", "integer NOT NULL DEFAULT 0"),
    ("season_moneyline_total",   "integer NOT NULL DEFAULT 0"),
    ("season_prop_correct",      "integer NOT NULL DEFAULT 0"),
    ("season_prop_total",        "integer NOT NULL DEFAULT 0"),
    ("week_accuracy",            "double precision NOT NULL DEFAULT 0"),
    ("season_accuracy",          "double precision NOT NULL DEFAULT 0"),
    ("moneyline_accuracy",       "double precision NOT NULL DEFAULT 0"),
    ("prop_accuracy",            "double precision NOT NULL DEFAULT 0"),
]

def make_add_if_not_exists(table, col, ddl):
    return (
        f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{col}" {ddl};',
        f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{col}";'
    )

class Migration(migrations.Migration):
    dependencies = [
        ("predictions", "0013_userstathistory_delete_rankhistory_and_more"),
    ]

    operations = [
        # Guarded adds for any columns this migration previously tried to add
        *[
            migrations.RunSQL(*make_add_if_not_exists("predictions_userstathistory", col, ddl))
            for col, ddl in USERSTAT_COLS
        ],

        # If 0014 also dropped/created other tables or indexes,
        # keep those here (convert to IF EXISTS/IF NOT EXISTS form).
        # Example patterns you can copy if needed:
        # migrations.RunSQL(
        #     'DROP TABLE IF EXISTS "predictions_userstreak";',
        #     '/* no-op reverse */'
        # ),
        # migrations.RunSQL(
        #     'CREATE INDEX IF NOT EXISTS "predictions_userstathistory_points_idx" '
        #     'ON "predictions_userstathistory" ("total_points" DESC);',
        #     'DROP INDEX IF EXISTS "predictions_userstathistory_points_idx";'
        # ),
    ]
