# predictions/utils/ranking_utils.py
from typing import List, Dict

def assign_dense_ranks(rows: List[Dict], points_key: str = 'total_points') -> List[Dict]:
    """
    Dense ranking (what we want): 1,2,2,3
    - Ties share the same rank
    - Next distinct score gets the next sequential rank (no skips)
    Sorting: points desc, then username asc for determinism.
    """
    rows.sort(key=lambda r: (-r.get(points_key, 0), str(r.get('username', '')).lower()))
    prev_points = object()  # sentinel
    current_rank = 0
    for r in rows:
        pts = r.get(points_key, 0)
        if pts != prev_points:
            current_rank += 1
            prev_points = pts
        r['rank'] = current_rank
    return rows

# Back-compat: keep the old function name but switch it to dense behavior.
# If you explicitly need 1,2,2,4 (competition) later, add a new helper.
def assign_competition_ranks(rows: List[Dict], points_key: str = 'total_points') -> List[Dict]:
    """
    Backward-compatible alias now implementing DENSE ranking (1,2,2,3).
    Previously this did 'competition' (1,2,2,4). We've standardized on dense.
    """
    return assign_dense_ranks(rows, points_key=points_key)
