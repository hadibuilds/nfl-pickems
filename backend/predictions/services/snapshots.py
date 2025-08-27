# predictions/services/snapshots.py
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone

from predictions.models import Top3Snapshot, CorrectionEvent
from predictions.services.top3_sql import publish_top3_from_db

@transaction.atomic
def publish_after_snapshot(window_key: str, correction_event: Optional[CorrectionEvent]=None) -> Tuple[Top3Snapshot, bool]:
    """
    Build the 'live' Top-K payload from DB and append a new AFTER snapshot
    only if it actually changed vs. the latest snapshot (idempotent).
    Returns (snapshot, created_flag).
    """
    payload = {"items": publish_top3_from_db()}  # keep shape consistent with your current payload
    latest = (
        Top3Snapshot.objects
        .filter(window_key=window_key)
        .order_by("-version")
        .first()
    )
    # if identical, do nothing
    if latest and (latest.payload or {}) == payload:
        return latest, False

    next_version = (latest.version + 1) if latest else 1
    snap = Top3Snapshot.objects.create(
        window_key=window_key,
        version=next_version,
        payload=payload,
        correction_applied=bool(correction_event),
        correction_event=correction_event,
        # if model doesn't auto_now_add a created_at, add created_at=timezone.now()
    )
    return snap, True
