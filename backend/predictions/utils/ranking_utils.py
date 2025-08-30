# predictions/utils/ranking_utils.py
from typing import List, Dict, Any

def assign_dense_ranks(rows: List[Dict[str, Any]],
                       points_key: str = "season_cume_points",
                       rank_key: str = "rank",
                       name_key: str = "username") -> List[Dict[str, Any]]:
    """
    Dense rank (1,2,2,3) on rows in-place and returned.
    - Sorts by points desc, then username asc for stability
    - Treats missing/None/NaN as 0
    """
    # normalize points
    for r in rows:
        v = r.get(points_key, 0)
        try:
            r[points_key] = int(v) if v is not None else 0
        except (TypeError, ValueError):
            r[points_key] = 0

    # stable sort before ranking
    rows.sort(key=lambda x: (-x.get(points_key, 0), str(x.get(name_key, "")).lower()))

    # assign dense ranks (1-based)
    rank = 0
    prev_points = None
    for idx, r in enumerate(rows):
        pts = r.get(points_key, 0)
        if prev_points is None or pts < prev_points:
            rank = idx + 1
            prev_points = pts
        r[rank_key] = rank

    return rows

# Back-compat: keep the old function name but switch it to dense behavior.
# If you explicitly need 1,2,2,4 (competition) later, add a new helper.
def assign_competition_ranks(rows: List[Dict], points_key: str = 'season_cume_points') -> List[Dict]:
    """
    Backward-compatible alias now implementing DENSE ranking (1,2,2,3).
    Previously this did 'competition' (1,2,2,4). We've standardized on dense.
    """
    return assign_dense_ranks(rows, points_key=points_key)
