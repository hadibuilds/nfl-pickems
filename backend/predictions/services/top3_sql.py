# Publisher — ask DB for Top-3 (no Python loops), snapshot when needed

from django.db import connection
from django.db.models import F, Window, Max
from django.db.models.functions import DenseRank
from django.db import IntegrityError, transaction

from predictions.models import UserSeasonTotals, Top3Snapshot

def _refresh_mv_if_needed():
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_season_totals_mv;")

def fetch_top3_payload():
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

def publish_top3_from_db():
    _refresh_mv_if_needed()
    return fetch_top3_payload()


def snapshot_and_publish(window_key: str, force: bool = False, keep_last_n: int = 2):
    data = publish_top3_from_db()
    last = (
        Top3Snapshot.objects
        .filter(window_key=window_key)
        .order_by("-version")
        .first()
    )
    if last and (not force) and last.payload == data:
        return data

    new_ver = (last.version if last else 0) + 1
    try:
        with transaction.atomic():
            Top3Snapshot.objects.create(window_key=window_key, version=new_ver, payload=data)
    except IntegrityError:
        # Someone else wrote the same version milliseconds earlier; ignore and continue.
        pass

    # Keep only latest N
    stale_ids = list(
        Top3Snapshot.objects
        .filter(window_key=window_key)
        .order_by("-version")
        .values_list("pk", flat=True)[keep_last_n:]
    )
    if stale_ids:
        Top3Snapshot.objects.filter(pk__in=stale_ids).delete()

    return data