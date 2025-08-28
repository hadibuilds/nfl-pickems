# analytics/migrations/0002_materialized_views.py
from django.db import migrations

MV_DELTAS = "user_window_deltas_mv"
MV_CUME = "user_window_cume_mv"  # keep name consistent everywhere

def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    # Resolve actual table names from models created in analytics 0001
    UserWindowDeltas = apps.get_model("analytics", "UserWindowDeltas")
    UserWindowCumulative = apps.get_model("analytics", "UserWindowCumulative")
    deltas_table = UserWindowDeltas._meta.db_table
    cume_table = UserWindowCumulative._meta.db_table

    # NOTE:
    # These SELECT bodies are placeholders that mirror your base tables.
    # Replace the SELECT bodies with your real aggregation if you intend the MVs
    # to compute more than a straight snapshot (e.g., joins, ranks).
    create_deltas = f"""
    CREATE MATERIALIZED VIEW IF NOT EXISTS {MV_DELTAS} AS
    SELECT *
    FROM {deltas_table};
    """

    # Unique index needed if you want REFRESH CONCURRENTLY
    # Adapt the key columns to match your schema (user_id & window_key are typical)
    create_deltas_idx = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'i'
              AND c.relname = '{MV_DELTAS}_uniq'
        ) THEN
            CREATE UNIQUE INDEX {MV_DELTAS}_uniq
            ON {MV_DELTAS} (user_id, window_key);
        END IF;
    END$$;
    """

    create_cume = f"""
    CREATE MATERIALIZED VIEW IF NOT EXISTS {MV_CUME} AS
    SELECT *
    FROM {cume_table};
    """

    create_cume_idx = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'i'
              AND c.relname = '{MV_CUME}_uniq'
        ) THEN
            CREATE UNIQUE INDEX {MV_CUME}_uniq
            ON {MV_CUME} (user_id, window_key);
        END IF;
    END$$;
    """

    with schema_editor.connection.cursor() as cur:
        cur.execute(create_deltas)
        cur.execute(create_deltas_idx)
        cur.execute(create_cume)
        cur.execute(create_cume_idx)

def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    drop = f"""
    DROP MATERIALIZED VIEW IF EXISTS {MV_CUME} CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS {MV_DELTAS} CASCADE;
    """
    with schema_editor.connection.cursor() as cur:
        cur.execute(drop)

class Migration(migrations.Migration):
    dependencies = [
        ("games", "0001_initial"),
        ("predictions", "0001_initial"),
        ("analytics", "0001_initial"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]