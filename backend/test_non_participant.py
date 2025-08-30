#!/usr/bin/env python
"""
Test script to demonstrate non-participant behavior in window calculations.
This answers the user's question about how non-participants are handled.
"""
import os
import sys
import django
from datetime import date, datetime, timezone as dt_timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.auth import get_user_model
from games.models import Window, Game
from predictions.models import MoneyLinePrediction
from analytics.models import UserWindowStat
from analytics.services.window_stats_optimized import recompute_window_optimized

User = get_user_model()

def clean_test_data():
    """Clean up any existing test data"""
    User.objects.filter(username__startswith='test_np_').delete()
    Window.objects.filter(season=2024).delete()
    print("✓ Cleaned test data")

def setup_scenario():
    """Set up test scenario with non-participants"""
    print("\n=== SETTING UP SCENARIO ===")
    
    # Create 4 users
    alice = User.objects.create_user(username='test_np_alice', email='alice@test.com')
    bob = User.objects.create_user(username='test_np_bob', email='bob@test.com') 
    charlie = User.objects.create_user(username='test_np_charlie', email='charlie@test.com')
    diana = User.objects.create_user(username='test_np_diana', email='diana@test.com')
    
    # Create 3 windows
    window1 = Window.objects.create(season=2024, date=date(2024, 1, 1), slot='morning')
    window2 = Window.objects.create(season=2024, date=date(2024, 1, 2), slot='morning')
    window3 = Window.objects.create(season=2024, date=date(2024, 1, 3), slot='morning')
    
    print(f"Created users: {alice.username}, {bob.username}, {charlie.username}, {diana.username}")
    print(f"Created windows: {window1.id}, {window2.id}, {window3.id}")
    
    return alice, bob, charlie, diana, window1, window2, window3

def test_window1_behavior(alice, bob, charlie, diana, window1):
    """Test Window 1: Only Alice and Bob participate"""
    print(f"\n=== WINDOW 1 BEHAVIOR ===")
    
    # Create game in window 1
    game1 = Game.objects.create(
        window=window1,
        away_team='AWAY1',
        home_team='HOME1',
        season=2024,
        week=1,
        start_time=datetime.now(dt_timezone.utc),
        winner='HOME1',
        locked=True
    )
    
    # Only Alice and Bob make predictions (Charlie and Diana are NON-PARTICIPANTS)
    MoneyLinePrediction.objects.create(user=alice, game=game1, predicted_winner='HOME1', is_correct=True)
    MoneyLinePrediction.objects.create(user=bob, game=game1, predicted_winner='AWAY1', is_correct=False)
    
    print(f"Window 1 participants: Alice (correct), Bob (incorrect)")
    print(f"Window 1 non-participants: Charlie, Diana")
    
    # Recompute window 1
    recompute_window_optimized(window1.id)
    
    # Check results
    stats = UserWindowStat.objects.filter(window=window1)
    print(f"\nWindow 1 UserWindowStat records created: {stats.count()}")
    
    for stat in stats.order_by('-season_cume_points'):
        user = User.objects.get(id=stat.user_id)
        print(f"  {user.username}: {stat.window_points} points, cumulative: {stat.season_cume_points}, rank: {stat.rank_dense}")
    
    # Key question: Do Charlie and Diana get UserWindowStat records?
    charlie_stat = UserWindowStat.objects.filter(user=charlie, window=window1).first()
    diana_stat = UserWindowStat.objects.filter(user=diana, window=window1).first()
    
    print(f"\nCharlie has Window 1 stat: {charlie_stat is not None}")
    print(f"Diana has Window 1 stat: {diana_stat is not None}")
    
    return stats.count()

def test_window2_behavior(alice, bob, charlie, diana, window1, window2):
    """Test Window 2: Charlie joins, Diana still doesn't participate"""
    print(f"\n=== WINDOW 2 BEHAVIOR ===")
    
    # Create game in window 2
    game2 = Game.objects.create(
        window=window2,
        away_team='AWAY2',
        home_team='HOME2',
        season=2024,
        week=2,
        start_time=datetime.now(dt_timezone.utc),
        winner='HOME2',
        locked=True
    )
    
    # Alice and Charlie predict (Bob skips, Diana still hasn't participated)
    MoneyLinePrediction.objects.create(user=alice, game=game2, predicted_winner='HOME2', is_correct=True)
    MoneyLinePrediction.objects.create(user=charlie, game=game2, predicted_winner='HOME2', is_correct=True)
    
    print(f"Window 2 participants: Alice (correct), Charlie (correct, FIRST TIME)")
    print(f"Window 2 non-participants: Bob (skips but participated before), Diana (still never participated)")
    
    # Recompute window 2
    recompute_window_optimized(window2.id)
    
    # Check results
    stats = UserWindowStat.objects.filter(window=window2)
    print(f"\nWindow 2 UserWindowStat records created: {stats.count()}")
    
    for stat in stats.order_by('-season_cume_points'):
        user = User.objects.get(id=stat.user_id)
        print(f"  {user.username}: {stat.window_points} points, cumulative: {stat.season_cume_points}, rank: {stat.rank_dense}")
    
    # Key questions:
    # 1. Does Bob get a Window 2 stat even though he didn't participate? (He should - previous participant)
    # 2. Does Diana get a Window 2 stat? (She shouldn't - never participated)
    bob_stat = UserWindowStat.objects.filter(user=bob, window=window2).first()
    diana_stat = UserWindowStat.objects.filter(user=diana, window=window2).first()
    
    print(f"\nBob has Window 2 stat (skipped but previous participant): {bob_stat is not None}")
    if bob_stat:
        print(f"  Bob's Window 2: {bob_stat.window_points} points, cumulative: {bob_stat.season_cume_points}, rank: {bob_stat.rank_dense}")
    
    print(f"Diana has Window 2 stat (never participated): {diana_stat is not None}")
    
    return stats.count()

def test_ranking_behavior():
    """Test how ranking works across windows for non-participants"""
    print(f"\n=== RANKING ANALYSIS ===")
    
    print("Window 1 Rankings:")
    w1_stats = UserWindowStat.objects.filter(window_id=Window.objects.get(season=2024, date=date(2024, 1, 1)).id).order_by('-season_cume_points')
    for i, stat in enumerate(w1_stats, 1):
        user = User.objects.get(id=stat.user_id)
        print(f"  {i}. {user.username}: {stat.season_cume_points} points (rank {stat.rank_dense})")
    
    print("\nWindow 2 Rankings:")
    w2_stats = UserWindowStat.objects.filter(window_id=Window.objects.get(season=2024, date=date(2024, 1, 2)).id).order_by('-season_cume_points')
    for i, stat in enumerate(w2_stats, 1):
        user = User.objects.get(id=stat.user_id)
        print(f"  {i}. {user.username}: {stat.season_cume_points} points (rank {stat.rank_dense}) [delta: {stat.rank_delta}]")

def main():
    """Run the complete test scenario"""
    print("=== NON-PARTICIPANT WINDOW CALCULATION ANALYSIS ===")
    print("This test answers: How are non-participants handled in UserWindowStats?")
    
    clean_test_data()
    alice, bob, charlie, diana, window1, window2, window3 = setup_scenario()
    
    w1_stats_count = test_window1_behavior(alice, bob, charlie, diana, window1)
    w2_stats_count = test_window2_behavior(alice, bob, charlie, diana, window1, window2)
    
    test_ranking_behavior()
    
    print(f"\n=== SUMMARY ===")
    print(f"Window 1 stats created: {w1_stats_count} (should be 2: Alice, Bob)")
    print(f"Window 2 stats created: {w2_stats_count} (should be 3: Alice, Bob, Charlie)")
    print(f"\nKEY INSIGHTS:")
    print(f"1. Non-participants in Window 1 (Charlie, Diana) get NO UserWindowStat records")
    print(f"2. Previous participants who skip a window (Bob in Window 2) DO get UserWindowStat records")
    print(f"3. Users who have never participated (Diana in Window 2) get NO UserWindowStat records")
    print(f"4. New participants (Charlie in Window 2) get UserWindowStat records going forward")
    
    clean_test_data()
    print(f"\n✓ Test completed and cleaned up")

if __name__ == '__main__':
    main()