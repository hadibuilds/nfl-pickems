# predictions/migrations/0015_remove_seasonstats_predictions_seasonstat_perf_idx_and_more.py
from django.db import migrations

SQL_DROPS = [
    # This index never existed on prod; make it safe.
    'DROP INDEX IF EXISTS "predictions_seasonstat_perf_idx";',

    # These names were targeted in 0015 but don’t match 0013's actual names.
    'DROP INDEX IF EXISTS "predictions_userstat_user_week_idx";',
    'DROP INDEX IF EXISTS "predictions_userstat_week_rank_idx";',
    'DROP INDEX IF EXISTS "predictions_userstat_points_idx";',
]

class Migration(migrations.Migration):
    dependencies = [
        ('predictions', '0014_update_for_rank_based_system'),
    ]

    operations = [
        migrations.RunSQL(
            sql=" ".join(SQL_DROPS),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]