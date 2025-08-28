# analytics/services/top3_sql.py - CRITICAL FIX: Database query issues

from django.db import connection
from django.db.models import F, Window
from django.db.models.functions import DenseRank
from django.db import IntegrityError, transaction

from ..models import UserSeasonTotals, Top3Snapshot

def _refresh_mv_if_needed():
    """CRITICAL: Only refresh if using PostgreSQL"""
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_season_totals_mv;")

def fetch_top3_payload():
    """CRITICAL FIX: Add error handling for missing data"""
    try:
        qs = (
            UserSeasonTotals.objects
            .select_related("user")
            .annotate(
                username=F("user__username"),
                rank=Window(
                    expression=DenseRank(),
                    order_by=[F("total_points").desc(), F("ml_points").desc(), F("user_id").asc()],
                )
            )
            .filter(rank__lte=3)
            .order_by("rank", "-total_points", "-ml_points", "user_id")
            .values("user_id", "username", "ml_points", "prop_points", "total_points", "rank")
        )
        return list(qs)
    except Exception as e:
        # CRITICAL: Don't crash if materialized view is empty or broken
        print(f"Warning: fetch_top3_payload failed: {e}")
        return []

def publish_top3_from_db():
    """CRITICAL FIX: Always refresh MV before querying"""
    _refresh_mv_if_needed()
    return fetch_top3_payload()

def snapshot_and_publish(window_key: str, force: bool = False, keep_last_n: int = 2):
    """CRITICAL FIX: Add error handling for snapshot creation"""
    try:
        data = publish_top3_from_db()
        
        # Don't create empty snapshots
        if not data:
            print(f"Warning: No data for snapshot {window_key}, skipping")
            return []
        
        last = (
            Top3Snapshot.objects
            .filter(window_key=window_key)
            .order_by("-version")
            .first()
        )
        
        # Skip if data hasn't changed and not forced
        if last and (not force) and last.payload == data:
            return data

        new_ver = (last.version if last else 0) + 1
        
        try:
            with transaction.atomic():
                Top3Snapshot.objects.create(
                    window_key=window_key, 
                    version=new_ver, 
                    payload=data
                )
        except IntegrityError:
            # Someone else created the same version concurrently
            print(f"IntegrityError creating snapshot {window_key} v{new_ver}, ignoring")
            pass

        # CRITICAL: Clean up old snapshots to prevent table bloat
        stale_ids = list(
            Top3Snapshot.objects
            .filter(window_key=window_key)
            .order_by("-version")
            .values_list("pk", flat=True)[keep_last_n:]
        )
        if stale_ids:
            deleted_count = Top3Snapshot.objects.filter(pk__in=stale_ids).delete()[0]
            print(f"Cleaned up {deleted_count} old snapshots for {window_key}")

        return data
        
    except Exception as e:
        print(f"Critical error in snapshot_and_publish: {e}")
        return []