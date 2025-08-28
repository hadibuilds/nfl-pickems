# analytics/services/windowed_rankings.py - Core windowed ranking logic

"""
Windowed Ranking Services - Core business logic for window-based standings:

DELTA CALCULATION:
- calculate_window_deltas(): What each user earned in a specific window
- refresh_all_deltas(): Recalculate all deltas (after corrections)

CUMULATIVE CALCULATION: 
- calculate_window_cumulative(): Running totals + ranks after each window
- calculate_trends(): Compare consecutive windows for trend arrows

WINDOW MANAGEMENT:
- get_window_key_from_game(): Generate window_key from game start_time
- close_window(): Mark window complete and calculate final ranks
- is_window_complete(): Check if all games/props in window have results
"""

from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
import pytz

from games.models import Game, PropBet
from predictions.models import Prediction, PropBetPrediction
from ..models import UserWindowDeltas, UserWindowCumulative
from ..utils.ranking_utils import assign_dense_ranks

User = get_user_model()

# =============================================================================
# WINDOW KEY GENERATION - PT timezone handling
# =============================================================================

def get_window_key_from_game(game):
    """
    Generate window_key from game start_time in PT timezone.
    Format: "YYYY-MM-DD:morning|afternoon|late"
    
    Boundaries (PT):
    - morning: 00:00 - 12:59
    - afternoon: 13:00 - 16:59  
    - late: 17:00 - 23:59
    """
    if not game.start_time:
        return None
        
    # Convert to PT timezone
    pt_tz = pytz.timezone('America/Los_Angeles')
    pt_time = game.start_time.astimezone(pt_tz)
    
    # Get date part
    date_str = pt_time.strftime('%Y-%m-%d')
    
    # Determine slot based on hour
    hour = pt_time.hour
    if hour < 13:  # 0-12
        slot = 'morning'
    elif hour < 17:  # 13-16
        slot = 'afternoon' 
    else:  # 17-23
        slot = 'late'
    
    return f"{date_str}:{slot}"


def get_current_season():
    """Get current season year"""
    return timezone.now().year


# =============================================================================
# DELTA CALCULATION - What happened in each window
# =============================================================================

def calculate_window_deltas(season, window_key, force_refresh=False):
    """
    Calculate point deltas for all users in a specific window.
    Returns dict of {user_id: {'ml': X, 'prop': Y, 'total': Z}}
    """
    
    # Get all games in this window
    games_in_window = Game.objects.filter(
        season=season,
        window_key=window_key,
        winner__isnull=False  # Only completed games
    )
    
    if not games_in_window.exists():
        return {}
    
    # Calculate ML deltas
    ml_deltas = {}
    for pred in Prediction.objects.filter(game__in=games_in_window, is_correct=True):
        user_id = pred.user_id
        ml_deltas[user_id] = ml_deltas.get(user_id, 0) + 1
    
    # Calculate prop deltas  
    prop_deltas = {}
    completed_props = PropBet.objects.filter(
        game__in=games_in_window,
        correct_answer__isnull=False
    )
    
    for prop_pred in PropBetPrediction.objects.filter(prop_bet__in=completed_props, is_correct=True):
        user_id = prop_pred.user_id
        prop_deltas[user_id] = prop_deltas.get(user_id, 0) + 2  # Props worth 2 points
    
    # Combine deltas
    all_user_ids = set(ml_deltas.keys()) | set(prop_deltas.keys())
    
    deltas = {}
    for user_id in all_user_ids:
        ml_points = ml_deltas.get(user_id, 0)
        prop_points = prop_deltas.get(user_id, 0)
        deltas[user_id] = {
            'ml': ml_points,
            'prop': prop_points, 
            'total': ml_points + prop_points
        }
    
    return deltas


def store_window_deltas(season, window_key, deltas):
    """
    Store calculated deltas in UserWindowDeltas table.
    Creates records for users with points, ensures all users have records.
    """
    
    with transaction.atomic():
        # Delete existing records for this window (in case of recalculation)
        UserWindowDeltas.objects.filter(season=season, window_key=window_key).delete()
        
        # Create records for all users (even if 0 points)
        records_to_create = []
        
        for user in User.objects.all():
            user_deltas = deltas.get(user.id, {'ml': 0, 'prop': 0, 'total': 0})
            
            record = UserWindowDeltas(
                user=user,
                season=season,
                window_key=window_key,
                ml_points_delta=user_deltas['ml'],
                prop_points_delta=user_deltas['prop'],
                total_delta=user_deltas['total']
            )
            records_to_create.append(record)
        
        UserWindowDeltas.objects.bulk_create(records_to_create)
        
    return len(records_to_create)


# =============================================================================
# CUMULATIVE CALCULATION - Running totals and ranks
# =============================================================================

def calculate_window_cumulative(season, through_window_key=None, start_window_key=None):
    """
    Calculate cumulative totals and ranks for all windows in season.
    If through_window_key specified, only calculate through that window.
    """
    
    # Get all deltas for season, ordered by window_seq
    deltas_qs = UserWindowDeltas.objects.filter(season=season).order_by('window_seq', 'user')

    # Optional: only recompute from a starting window forward, seeding with prior baseline
    baseline_totals = None
    if start_window_key:
        start_seq = UserWindowDeltas.objects.filter(season=season, window_key=start_window_key).values_list('window_seq', flat=True).first()
        if start_seq:
            deltas_qs = deltas_qs.filter(window_seq__gte=start_seq)
            # Seed baseline cumulative totals from the last cumulative BEFORE start_seq
            baseline_totals = {}
            prior_qs = (UserWindowCumulative.objects
                        .filter(season=season, window_seq__lt=start_seq)
                        .order_by('user_id', '-window_seq'))
            # Take the latest per user
            seen = set()
            for rec in prior_qs:
                if rec.user_id in seen:
                    continue
                baseline_totals[rec.user_id] = {'ml': rec.cume_ml_after, 'prop': rec.cume_prop_after, 'total': rec.cume_total_after}
                seen.add(rec.user_id)
    
    if through_window_key:
        target_seq = UserWindowDeltas.objects.filter(
            season=season, 
            window_key=through_window_key
        ).values_list('window_seq', flat=True).first()
        
        if target_seq:
            deltas_qs = deltas_qs.filter(window_seq__lte=target_seq)
    
    # Group by window_key for processing
    windows_processed = []
    current_window_data = []
    current_window_key = None
    
    # Track cumulative totals per user across windows
    user_cume_totals = baseline_totals.copy() if 'baseline_totals' in locals() and baseline_totals else {}
    
    for delta in deltas_qs:
        # New window - process previous window
        if current_window_key and delta.window_key != current_window_key:
            ranks = _calculate_ranks_for_window(current_window_data, user_cume_totals, current_window_key, season)
            windows_processed.extend(ranks)
            current_window_data = []
        
        # Update cumulative totals
        user_id = delta.user_id
        if user_id not in user_cume_totals:
            user_cume_totals[user_id] = {'ml': 0, 'prop': 0, 'total': 0}
        
        user_cume_totals[user_id]['ml'] += delta.ml_points_delta
        user_cume_totals[user_id]['prop'] += delta.prop_points_delta  
        user_cume_totals[user_id]['total'] += delta.total_delta
        
        current_window_data.append({
            'user_id': user_id,
            'window_key': delta.window_key,
            'window_seq': delta.window_seq,
            'cume_ml': user_cume_totals[user_id]['ml'],
            'cume_prop': user_cume_totals[user_id]['prop'],
            'cume_total': user_cume_totals[user_id]['total']
        })
        
        current_window_key = delta.window_key
    
    # Process final window
    if current_window_data:
        ranks = _calculate_ranks_for_window(current_window_data, user_cume_totals, current_window_key, season)
        windows_processed.extend(ranks)
    
    return windows_processed


def _calculate_ranks_for_window(window_data, user_cume_totals, window_key, season):
    """
    Calculate dense ranks for users in a specific window.
    Returns list of UserWindowCumulative records ready for bulk_create.
    """
    
    # Prepare data for ranking
    rank_data = []
    for item in window_data:
        rank_data.append({
            'user_id': item['user_id'],
            'username': usernames_map.get(item['user_id'], ''),  # from prefetch map; tie-breaker
            'total_points': item['cume_total'],
            'cume_ml': item['cume_ml'],
            'cume_prop': item['cume_prop'],
            'window_key': item['window_key'],
            'window_seq': item['window_seq']
        })
    
    # Apply dense ranking

    # Prefetch usernames in bulk to avoid N+1, and build deterministic tie-breakers
    user_ids_set = {it['user_id'] for it in window_data}
    usernames_map = dict(User.objects.filter(id__in=user_ids_set).values_list('id', 'username'))
    for rd in rank_data:
        rd['username_lower'] = (rd.get('username') or '').lower()
        rd['user_id_int'] = int(rd['user_id'])
    # Deterministic ordering for ties before dense rank: (-points, username_lower, user_id)
    rank_data.sort(key=lambda r: (-int(r['total_points']), r['username_lower'], r['user_id_int']))
    assign_dense_ranks(rank_data, points_key='total_points')
    
    # Get previous window ranks for trend calculation
    prev_ranks = _get_previous_window_ranks(season, window_key)
    
    # Determine if this is first window (no trend display)
    is_first_window = _is_first_real_window(season, window_key)
    
    # Create UserWindowCumulative records
    records = []
    for item in rank_data:
        user_id = item['user_id']
        rank_after = item['rank']
        rank_before = prev_ranks.get(user_id)
        
        # Calculate rank change
        rank_change = 0
        if rank_before is not None:
            rank_change = rank_before - rank_after
        
        record = UserWindowCumulative(
            user_id=user_id,
            season=season,
            window_key=item['window_key'],
            window_seq=item['window_seq'],
            cume_ml_after=item['cume_ml'],
            cume_prop_after=item['cume_prop'],
            cume_total_after=item['total_points'],
            rank_after=rank_after,
            rank_before=rank_before,
            rank_change=rank_change,
            display_trend=not is_first_window
        )
        records.append(record)
    
    return records


def _get_previous_window_ranks(season, current_window_key):
    """Get rank_after from previous window for trend calculation"""
    current_seq = UserWindowDeltas.objects.filter(
        season=season, 
        window_key=current_window_key
    ).values_list('window_seq', flat=True).first()
    
    if not current_seq:
        return {}
    
    # Find previous window
    prev_window = UserWindowCumulative.objects.filter(
        season=season,
        window_seq__lt=current_seq
    ).order_by('-window_seq').values_list('window_key', flat=True).first()
    
    if not prev_window:
        # First window - everyone starts at last place
        user_count = User.objects.count()
        return {user.id: user_count for user in User.objects.all()}
    
    # Get ranks from previous window
    prev_ranks = {}
    for record in UserWindowCumulative.objects.filter(season=season, window_key=prev_window):
        prev_ranks[record.user_id] = record.rank_after
    
    return prev_ranks


def _is_first_real_window(season, window_key):
    """Check if this is the first window with actual results (no trend display)"""
    window_seq = UserWindowDeltas.objects.filter(
        season=season, 
        window_key=window_key
    ).values_list('window_seq', flat=True).first()
    
    if not window_seq:
        return True
    
    # Check if any earlier windows exist with results
    earlier_windows = UserWindowDeltas.objects.filter(
        season=season,
        window_seq__lt=window_seq
    ).exists()
    
    return not earlier_windows


def store_window_cumulative(season, cumulative_records):
    """
    Store calculated cumulative records in UserWindowCumulative table.
    Replaces existing records for affected windows.
    """
    
    if not cumulative_records:
        return 0
    
    # Get window keys being updated
    window_keys = list(set(record.window_key for record in cumulative_records))
    
    with transaction.atomic():
        # Delete existing records for these windows
        UserWindowCumulative.objects.filter(
            season=season,
            window_key__in=window_keys
        ).delete()
        
        # Bulk create new records
        UserWindowCumulative.objects.bulk_create(cumulative_records)
    
    return len(cumulative_records)


# =============================================================================
# WINDOW COMPLETION - Check if window ready to close
# =============================================================================

def is_window_complete(window_key, season=None):
    """
    Check if all games and props in a window have results.
    Window is complete when all games have winners AND all props have correct_answer.
    """
    season = season or get_current_season()
    
    # Get all games in this window
    games_in_window = Game.objects.filter(window_key=window_key)
    if season:
        games_in_window = games_in_window.filter(season=season)
    
    if not games_in_window.exists():
        return False
    
    # Check if any games missing winners
    incomplete_games = games_in_window.filter(winner__isnull=True)
    if incomplete_games.exists():
        return False
    
    # Check if any props missing correct_answer
    incomplete_props = PropBet.objects.filter(
        game__in=games_in_window,
        correct_answer__isnull=True
    )
    if incomplete_props.exists():
        return False
    
    return True


# =============================================================================
# MAIN ORCHESTRATION - Full window processing
# =============================================================================

def process_window(season, window_key, force_refresh=False):
    """
    Complete window processing: calculate deltas -> cumulative -> store.
    Returns summary of what was processed.
    """
    # Safety: don't process partial windows unless explicitly forced
    if not force_refresh:
        # If the window has no completed games/props yet, it's not actionable
        if not is_window_complete(window_key, season=season):
            return {
                'window_key': window_key,
                'season': season,
                'delta_records_created': 0,
                'cumulative_records_created': 0,
                'skipped': True,
                'reason': 'window_incomplete'
            }
    """
    Complete window processing: calculate deltas -> cumulative -> store.
    Returns summary of what was processed.
    """
    
    # Step 1: Calculate deltas for this window
    deltas = calculate_window_deltas(season, window_key, force_refresh)
    
    # Step 2: Store deltas
    delta_count = store_window_deltas(season, window_key, deltas)
    
    # Step 3: Recalculate cumulative from this window forward
    cumulative_records = calculate_window_cumulative(season, through_window_key=None, start_window_key=window_key)
    
    # Step 4: Store cumulative
    cume_count = store_window_cumulative(season, cumulative_records)
    
    # Step 5: Refresh materialized views if PostgreSQL
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_window_deltas_mv;")
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY user_window_cume_mv;")
    
    return {
        'window_key': window_key,
        'season': season,
        'delta_records_created': delta_count,
        'cumulative_records_created': cume_count,
        'users_with_points': len([d for d in deltas.values() if d['total'] > 0]),
        'total_points_awarded': sum(d['total'] for d in deltas.values()),
        'window_complete': is_window_complete(window_key, season)
    }

# =============================================================================
# LIVE OVERLAY HELPERS
# =============================================================================

def get_last_closed_window_key(season):
    """Return the last closed (persisted) window_key for the season, or None."""
    return (UserWindowCumulative.objects
            .filter(season=season)
            .order_by('-window_seq')
            .values_list('window_key', flat=True)
            .first())

def get_window_status(season, window_key):
    """Return 'closed' if this window is persisted, 'in_progress' if not closed but has any results, else 'upcoming'."""
    if UserWindowCumulative.objects.filter(season=season, window_key=window_key).exists():
        return 'closed'
    # Any completed game or prop?
    has_any_game = Game.objects.filter(season=season, window_key=window_key).exists()
    has_any_completed_game = Game.objects.filter(season=season, window_key=window_key, winner__isnull=False).exists()
    has_any_completed_prop = PropBet.objects.filter(season=season, game__window_key=window_key, correct_answer__isnull=False).exists()
    if has_any_completed_game or has_any_completed_prop:
        return 'in_progress'
    return 'upcoming' if has_any_game else 'unknown'

def _dense_rank_sorted(items, key):
    """Assign dense ranks to a pre-sorted list of dicts by the value of key (descending)."""
    ranks = []
    prev = None
    rank = 0
    for idx, it in enumerate(items):
        score = it[key]
        if prev is None or score != prev:
            rank = rank + 1
            prev = score
        it['rank'] = rank
        ranks.append(it)
    return ranks

def compute_live_overlay(season, window_key):
    """Compute live totals and ranks for the given window_key using baseline from last closed window and current resolved deltas."""
    status = get_window_status(season, window_key)
    last_closed_key = get_last_closed_window_key(season)
    # Baseline from last closed cumulative
    baseline_map = {}
    if last_closed_key:
        for rec in UserWindowCumulative.objects.filter(season=season, window_key=last_closed_key):
            baseline_map[rec.user_id] = rec.cume_total_after

    # If the requested window is already closed, mirror the frozen snapshot
    if status == 'closed':
        live_items = []
        qs = UserWindowCumulative.objects.filter(season=season, window_key=window_key)
        uname_map = dict(User.objects.filter(
            id__in=qs.values_list('user_id', flat=True)
        ).values_list('id','username'))
        for rec in qs:
            live_items.append({
                'user_id': rec.user_id,
                'username_lower': (uname_map.get(rec.user_id,'') or '').lower(),
                'live_total_points': rec.cume_total_after
            })
        # sort and rank
        live_items.sort(key=lambda r: (-int(r['live_total_points']), r['username_lower'], int(r['user_id'])))
        _dense_rank_sorted(live_items, 'live_total_points')
        return {it['user_id']: {'live_total_points': it['live_total_points'], 'live_rank': it['rank']} for it in live_items}

    # Otherwise compute deltas for the target window (partial allowed: only resolved pieces count)
    deltas = calculate_window_deltas(season, window_key, force_refresh=True) or {}
    # Build user list: anyone in baseline or with deltas
    user_ids = set(baseline_map.keys()) | set(deltas.keys())
    if not user_ids:
        return {}
    # Prefetch usernames
    uname_map = dict(User.objects.filter(id__in=user_ids).values_list('id','username'))
    live_items = []
    for uid in user_ids:
        base = baseline_map.get(uid, 0)
        delta_total = (deltas.get(uid, {}) or {}).get('total', 0)
        live_total = int(base) + int(delta_total)
        live_items.append({
            'user_id': uid,
            'username_lower': (uname_map.get(uid,'') or '').lower(),
            'live_total_points': live_total
        })
    # sort and rank
    live_items.sort(key=lambda r: (-int(r['live_total_points']), r['username_lower'], int(r['user_id'])))
    _dense_rank_sorted(live_items, 'live_total_points')
    return {it['user_id']: {'live_total_points': it['live_total_points'], 'live_rank': it['rank']} for it in live_items}
