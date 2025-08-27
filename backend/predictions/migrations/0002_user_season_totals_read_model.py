# predictions/migrations/0002_user_season_totals_read_model.py
from django.db import migrations

def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    # Resolve table names at migration time (portable across renames/app-label changes)
    Prediction = apps.get_model("predictions", "Prediction")
    PropBetPrediction = apps.get_model("predictions", "PropBetPrediction")
    pred_tbl = Prediction._meta.db_table                  # e.g. "predictions_prediction"
    prop_tbl = PropBetPrediction._meta.db_table           # e.g. "predictions_propbetprediction"

    if vendor == "postgresql":
        sql = f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS user_season_totals_mv AS
        WITH unioned AS (
          SELECT user_id,
                 SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS ml_pts,
                 0 AS prop_pts
          FROM {pred_tbl}
          GROUP BY user_id

          UNION ALL

          SELECT user_id,
                 0 AS ml_pts,
                 2 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS prop_pts
          FROM {prop_tbl}
          GROUP BY user_id
        )
        SELECT user_id,
               SUM(ml_pts) AS ml_points,
               SUM(prop_pts) AS prop_points,
               SUM(ml_pts) + SUM(prop_pts) AS total_points
        FROM unioned
        GROUP BY user_id
        WITH NO DATA;
        """
        idx_sql = """
        CREATE UNIQUE INDEX IF NOT EXISTS user_season_totals_mv_user_id_idx
          ON user_season_totals_mv (user_id);
        """
        refresh_sql = "REFRESH MATERIALIZED VIEW user_season_totals_mv;"

        with schema_editor.connection.cursor() as cur:
            # Run as separate statements to keep things predictable
            cur.execute(sql)
            cur.execute(idx_sql)
            cur.execute(refresh_sql)

    else:
        # SQLite (and other non-PG backends): use a normal VIEW
        sql = f"""
        CREATE VIEW IF NOT EXISTS user_season_totals_mv AS
        WITH unioned AS (
          SELECT user_id,
                 SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS ml_pts,
                 0 AS prop_pts
          FROM {pred_tbl}
          GROUP BY user_id

          UNION ALL

          SELECT user_id,
                 0 AS ml_pts,
                 2 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS prop_pts
          FROM {prop_tbl}
          GROUP BY user_id
        )
        SELECT user_id,
               SUM(ml_pts) AS ml_points,
               SUM(prop_pts) AS prop_points,
               SUM(ml_pts) + SUM(prop_pts) AS total_points
        FROM unioned
        GROUP BY user_id;
        """
        with schema_editor.connection.cursor() as cur:
            cur.execute(sql)

def backwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cur:
        if vendor == "postgresql":
            # Drop MV and index (index drops with MV, but drop view is enough)
            cur.execute("DROP MATERIALIZED VIEW IF EXISTS user_season_totals_mv;")
        else:
            cur.execute("DROP VIEW IF EXISTS user_season_totals_mv;")

class Migration(migrations.Migration):
    dependencies = [
        ("predictions", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]
