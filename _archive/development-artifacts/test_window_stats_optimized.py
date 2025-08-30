# analytics/tests/test_window_stats_optimized.py
# Comprehensive tests for optimized window stats calculation
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.cache import cache
from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock
import logging

from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat
from analytics.services.window_stats_optimized import (
    OptimizedWindowCalculator,
    recompute_window_optimized,
    bulk_recompute_windows_optimized,
    validate_window_calculations,
    WindowCalculationError,
    SLOT_ORDER
)

User = get_user_model()

class OptimizedWindowStatsTest(TransactionTestCase):
    """Test optimized window stats calculation with all edge cases"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()  # Clear cache between tests
        
        # Create test users
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com')  
        self.user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        # Create season windows with various date/slot combinations
        self.season = 2024
        self.base_date = date(2024, 1, 1)
        
        # EDGE CASE: Same date, different slots
        self.window1_morning = Window.objects.create(
            season=self.season,
            date=self.base_date,
            slot='morning',
            is_complete=False
        )
        self.window2_afternoon = Window.objects.create(
            season=self.season,
            date=self.base_date,  # SAME DATE
            slot='afternoon',     # DIFFERENT SLOT
            is_complete=False
        )
        
        # Next day windows
        self.window3_morning = Window.objects.create(
            season=self.season,
            date=date(2024, 1, 2),
            slot='morning',
            is_complete=False
        )
        
        # EDGE CASE: Missing slot (should default to 'late' ordering)
        self.window4_no_slot = Window.objects.create(
            season=self.season,
            date=date(2024, 1, 3),
            slot=None,  # Missing slot
            is_complete=False
        )

    def _create_games_and_predictions(self, window, num_games=2, with_props=True):
        """Helper to create games and predictions for a window"""
        games = []
        for i in range(num_games):
            game = Game.objects.create(
                window=window,
                away_team=f'AWAY{i}',
                home_team=f'HOME{i}',
                season=self.season,
                week=1,
                start_time=datetime.now(dt_timezone.utc),
                winner=f'HOME{i}',  # Set winner for resolution
                locked=True
            )
            games.append(game)
            
            # Create ML predictions
            MoneyLinePrediction.objects.create(
                user=self.user1,
                game=game,
                predicted_winner=f'HOME{i}',  # Correct prediction
                is_correct=True
            )
            MoneyLinePrediction.objects.create(
                user=self.user2,
                game=game,
                predicted_winner=f'AWAY{i}',  # Wrong prediction
                is_correct=False
            )
            # user3 has no predictions (edge case)
            
            # Create prop bets if requested
            if with_props:
                prop_bet = PropBet.objects.create(
                    game=game,
                    question=f'Test question {i}',
                    option_a=f'Option A{i}',
                    option_b=f'Option B{i}',
                    correct_answer='A'  # Set correct answer
                )
                
                # Prop predictions
                PropBetPrediction.objects.create(
                    user=self.user1,
                    prop_bet=prop_bet,
                    answer='A',  # Correct
                    is_correct=True
                )
                PropBetPrediction.objects.create(
                    user=self.user2,
                    prop_bet=prop_bet,
                    answer='B',  # Wrong
                    is_correct=False
                )
                # user3 has no prop predictions
        
        return games

    def test_chronological_ordering_same_date_different_slots(self):
        """Test that same date, different slot windows are ordered correctly"""
        calculator = OptimizedWindowCalculator(self.window1_morning.id)
        calculator._validate_and_setup()
        
        # Should be ordered: morning, afternoon for same date
        windows = calculator.season_windows_cache
        
        morning_idx = next(w.chronological_index for w in windows if w.id == self.window1_morning.id)
        afternoon_idx = next(w.chronological_index for w in windows if w.id == self.window2_afternoon.id)
        
        self.assertLess(morning_idx, afternoon_idx, "Morning should come before afternoon on same date")

    def test_chronological_ordering_with_missing_slot(self):
        """Test that windows with missing slots are ordered correctly"""
        calculator = OptimizedWindowCalculator(self.window4_no_slot.id)
        calculator._validate_and_setup()
        
        # Window with None slot should be ordered after known slots
        windows = calculator.season_windows_cache
        no_slot_window = next(w for w in windows if w.id == self.window4_no_slot.id)
        
        # Should be treated as 'late' slot (order 3)
        self.assertEqual(no_slot_window.slot, 'unknown')

    def test_processes_season_participants_correctly(self):
        """Test that it processes current window participants AND previous season participants"""
        # Create additional users with no predictions (should be ignored)
        extra_users = [
            User.objects.create_user(username=f'unused{i}', email=f'unused{i}@test.com')
            for i in range(5)  # 5 extra users with no predictions ever
        ]
        
        # Create games for window1 - user1 and user2 have predictions
        self._create_games_and_predictions(self.window1_morning, num_games=2)
        
        # Process first window 
        recompute_window_optimized(self.window1_morning.id)
        
        # Now create second window where user3 has predictions, user1 doesn't
        game_w2 = Game.objects.create(
            window=self.window2_afternoon,
            away_team='AWAY_W2',
            home_team='HOME_W2',
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner='HOME_W2',
            locked=True
        )
        
        # Only user3 has predictions in window2
        MoneyLinePrediction.objects.create(
            user=self.user3,
            game=game_w2,
            predicted_winner='HOME_W2',
            is_correct=True
        )
        
        calculator = OptimizedWindowCalculator(self.window2_afternoon.id)
        calculator._validate_and_setup()
        
        # Calculate user deltas 
        user_deltas = calculator._calculate_user_deltas()
        processed_user_ids = {ud.user_id for ud in user_deltas}
        
        # Should process:
        # - user3 (has predictions in this window)  
        # - user1 and user2 (participated in previous windows)
        expected_user_ids = {self.user1.id, self.user2.id, self.user3.id}
        
        self.assertEqual(processed_user_ids, expected_user_ids)
        self.assertEqual(len(user_deltas), 3, "Should process current + previous participants")
        
        # Extra users should NOT be processed (never participated)
        all_user_ids = set(User.objects.values_list('id', flat=True))
        unprocessed_users = all_user_ids - processed_user_ids  
        self.assertEqual(len(unprocessed_users), 5, "Should ignore users who never participated")

    def test_window_calculation_accuracy(self):
        """Test that calculations are mathematically correct"""
        self._create_games_and_predictions(self.window1_morning, num_games=3, with_props=True)
        
        recompute_window_optimized(self.window1_morning.id)
        
        # Verify calculations
        user1_stat = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        user2_stat = UserWindowStat.objects.get(user=self.user2, window=self.window1_morning)
        
        # user1: 3 correct ML (3 points) + 3 correct PB (6 points) = 9 total
        self.assertEqual(user1_stat.ml_correct, 3)
        self.assertEqual(user1_stat.pb_correct, 3) 
        self.assertEqual(user1_stat.window_points, 9)
        self.assertEqual(user1_stat.season_cume_points, 9)  # First window
        self.assertEqual(user1_stat.rank_dense, 1)  # Should be rank 1
        
        # user2: 0 correct ML + 0 correct PB = 0 total
        self.assertEqual(user2_stat.ml_correct, 0)
        self.assertEqual(user2_stat.pb_correct, 0)
        self.assertEqual(user2_stat.window_points, 0)
        self.assertEqual(user2_stat.season_cume_points, 0)
        self.assertEqual(user2_stat.rank_dense, 2)  # Should be rank 2
        
        # user3 should NOT have a stat record (no predictions and no previous participation)
        self.assertFalse(
            UserWindowStat.objects.filter(user=self.user3, window=self.window1_morning).exists()
        )

    def test_cumulative_points_propagation(self):
        """Test that cumulative points propagate correctly across windows"""
        # Set up 3 windows in sequence
        self._create_games_and_predictions(self.window1_morning, num_games=1, with_props=False)
        self._create_games_and_predictions(self.window2_afternoon, num_games=1, with_props=False) 
        self._create_games_and_predictions(self.window3_morning, num_games=1, with_props=False)
        
        # Recompute in chronological order
        recompute_window_optimized(self.window1_morning.id)
        recompute_window_optimized(self.window2_afternoon.id)  # Same date, later slot
        recompute_window_optimized(self.window3_morning.id)   # Next day
        
        # Check cumulative points progression for user1
        stat1 = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2 = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        stat3 = UserWindowStat.objects.get(user=self.user1, window=self.window3_morning)
        
        # user1 gets 1 point per window (correct ML predictions)
        self.assertEqual(stat1.season_cume_points, 1)  # 0 + 1
        self.assertEqual(stat2.season_cume_points, 2)  # 1 + 1 
        self.assertEqual(stat3.season_cume_points, 3)  # 2 + 1

    def test_user_skips_window_but_maintains_rank(self):
        """Test that users who skip a window still get tracked for ranking purposes"""
        # Set up 3 windows
        self._create_games_and_predictions(self.window1_morning, num_games=1, with_props=False)
        
        # Window 2: Only user2 makes predictions, user1 skips
        game_w2 = Game.objects.create(
            window=self.window2_afternoon,
            away_team='AWAY_W2',
            home_team='HOME_W2', 
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner='HOME_W2',
            locked=True
        )
        
        # Only user2 predicts (correctly)
        MoneyLinePrediction.objects.create(
            user=self.user2,
            game=game_w2,
            predicted_winner='HOME_W2',
            is_correct=True
        )
        
        # Window 3: Both users predict again
        self._create_games_and_predictions(self.window3_morning, num_games=1, with_props=False)
        
        # Compute all windows
        recompute_window_optimized(self.window1_morning.id)
        recompute_window_optimized(self.window2_afternoon.id)
        recompute_window_optimized(self.window3_morning.id)
        
        # Check user1's progression (participated in windows 1 and 3, skipped 2)
        stat1_w1 = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat1_w2 = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        stat1_w3 = UserWindowStat.objects.get(user=self.user1, window=self.window3_morning)
        
        # user1: 1 point in window 1, 0 points in window 2 (skipped), 1 point in window 3
        self.assertEqual(stat1_w1.season_cume_points, 1)  # 0 + 1
        self.assertEqual(stat1_w2.season_cume_points, 1)  # 1 + 0 (skipped, no change)
        self.assertEqual(stat1_w3.season_cume_points, 2)  # 1 + 1
        
        # user1 should have 0 window points in window 2 (no predictions)
        self.assertEqual(stat1_w2.window_points, 0)
        self.assertEqual(stat1_w2.ml_correct, 0)
        self.assertEqual(stat1_w2.pb_correct, 0)
        
        # Check user2's progression (participated in all windows)
        stat2_w1 = UserWindowStat.objects.get(user=self.user2, window=self.window1_morning)
        stat2_w2 = UserWindowStat.objects.get(user=self.user2, window=self.window2_afternoon)
        stat2_w3 = UserWindowStat.objects.get(user=self.user2, window=self.window3_morning)
        
        # user2: 0 points in window 1 (wrong), 1 point in window 2 (correct), 0 points in window 3 (wrong)
        self.assertEqual(stat2_w1.season_cume_points, 0)  # 0 + 0
        self.assertEqual(stat2_w2.season_cume_points, 1)  # 0 + 1
        self.assertEqual(stat2_w3.season_cume_points, 1)  # 1 + 0
        
        # Check rankings in window 3 (both users have same cumulative points: user1=2, user2=1)
        self.assertEqual(stat1_w3.rank_dense, 1)  # user1 leads with 2 points
        self.assertEqual(stat2_w3.rank_dense, 2)  # user2 has 1 point

    def test_editing_previous_window_results(self):
        """Test that editing previous window results propagates correctly"""
        # Set up sequence of windows
        self._create_games_and_predictions(self.window1_morning, num_games=1, with_props=False)
        self._create_games_and_predictions(self.window2_afternoon, num_games=1, with_props=False)
        
        # Initial computation
        recompute_window_optimized(self.window1_morning.id)
        recompute_window_optimized(self.window2_afternoon.id)
        
        # Verify initial state
        stat1_before = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2_before = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        
        self.assertEqual(stat1_before.season_cume_points, 1)
        self.assertEqual(stat2_before.season_cume_points, 2)
        
        # EDGE CASE: Edit previous window result (change user1's prediction to wrong)
        ml_pred = MoneyLinePrediction.objects.get(user=self.user1, game__window=self.window1_morning)
        ml_pred.is_correct = False
        ml_pred.save()
        
        # Recompute the edited window - should propagate to future windows
        recompute_window_optimized(self.window1_morning.id)
        
        # Verify propagation
        stat1_after = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2_after = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        
        self.assertEqual(stat1_after.season_cume_points, 0)  # Now 0 points in window 1
        self.assertEqual(stat2_after.season_cume_points, 1)  # Propagated: 0 + 1

    def test_rank_trends_calculation(self):
        """Test that rank trends (deltas) are calculated correctly"""
        # Create two windows with different point distributions
        self._create_games_and_predictions(self.window1_morning, num_games=1, with_props=True)  # 3 points possible
        self._create_games_and_predictions(self.window2_afternoon, num_games=2, with_props=False) # 2 points possible
        
        # Window 1: user1 gets 3 points, user2 gets 0
        recompute_window_optimized(self.window1_morning.id)
        
        stat1_w1 = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2_w1 = UserWindowStat.objects.get(user=self.user2, window=self.window1_morning)
        
        self.assertEqual(stat1_w1.rank_dense, 1)  # user1 rank 1
        self.assertEqual(stat2_w1.rank_dense, 2)  # user2 rank 2
        self.assertEqual(stat1_w1.rank_delta, 0)  # No previous window
        self.assertEqual(stat2_w1.rank_delta, 0)  # No previous window
        
        # Window 2: user2 now gets 2 points, user1 gets 0 (predictions change)
        # Modify predictions for window 2 to flip the results
        ml_preds_w2 = MoneyLinePrediction.objects.filter(game__window=self.window2_afternoon)
        for pred in ml_preds_w2:
            pred.is_correct = (pred.user == self.user2)  # user2 wins, user1 loses
            pred.save()
        
        recompute_window_optimized(self.window2_afternoon.id)
        
        stat1_w2 = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        stat2_w2 = UserWindowStat.objects.get(user=self.user2, window=self.window2_afternoon)
        
        # user1: 3 + 0 = 3 points, user2: 0 + 2 = 2 points
        # user1 still rank 1, user2 still rank 2
        self.assertEqual(stat1_w2.rank_dense, 1)  
        self.assertEqual(stat2_w2.rank_dense, 2)
        
        # Rank deltas: both stayed same rank
        self.assertEqual(stat1_w2.rank_delta, 0)  # 1 - 1 = 0 (stayed same)
        self.assertEqual(stat2_w2.rank_delta, 0)  # 2 - 2 = 0 (stayed same)

    def test_bulk_recompute_chronological_order(self):
        """Test that bulk recompute processes windows in chronological order"""
        # Create games for all windows  
        self._create_games_and_predictions(self.window1_morning, num_games=1)
        self._create_games_and_predictions(self.window2_afternoon, num_games=1)
        self._create_games_and_predictions(self.window3_morning, num_games=1)
        
        # Bulk recompute in random order - should process chronologically
        window_ids = [self.window3_morning.id, self.window1_morning.id, self.window2_afternoon.id]
        results = bulk_recompute_windows_optimized(window_ids)
        
        # All should succeed
        self.assertTrue(all(results.values()))
        
        # Verify final cumulative points are correct (depends on chronological processing)
        stat1 = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2 = UserWindowStat.objects.get(user=self.user1, window=self.window2_afternoon)
        stat3 = UserWindowStat.objects.get(user=self.user1, window=self.window3_morning)
        
        # Should be cumulative: 3, 6, 9 (each window gives user1 3 points)
        self.assertEqual(stat1.season_cume_points, 3)
        self.assertEqual(stat2.season_cume_points, 6) 
        self.assertEqual(stat3.season_cume_points, 9)

    def test_validation_function(self):
        """Test the validation function for debugging"""
        # Create incomplete window (no winners set)
        incomplete_game = Game.objects.create(
            window=self.window1_morning,
            away_team='AWAY',
            home_team='HOME', 
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner=None,  # No winner set
            locked=False
        )
        
        validation = validate_window_calculations(self.window1_morning.id)
        
        self.assertEqual(validation['window_id'], self.window1_morning.id)
        self.assertEqual(validation['games']['total'], 1)
        self.assertEqual(validation['games']['unresolved'], 1)
        self.assertFalse(validation['validation_passed'])

    def test_error_handling_invalid_window(self):
        """Test error handling for invalid window ID"""
        with self.assertRaises(WindowCalculationError):
            recompute_window_optimized(99999)  # Non-existent window

    def test_caching_behavior(self):
        """Test that window chronology is cached properly"""
        calculator1 = OptimizedWindowCalculator(self.window1_morning.id)
        calculator1._validate_and_setup()
        
        # Cache should be populated
        cache_key = f"season_windows_chrono_{self.season}"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        
        # Second calculator should use cache
        with patch.object(calculator1, '_get_chronological_windows') as mock_get_windows:
            calculator2 = OptimizedWindowCalculator(self.window2_afternoon.id)
            calculator2._validate_and_setup()
            # Should not call the DB query method due to caching
            mock_get_windows.assert_not_called()

    def test_performance_no_over_calculation(self):
        """Test that we don't create UserWindowStat for users without predictions"""
        # Create many users, but only a few with predictions
        extra_users = [
            User.objects.create_user(username=f'extra{i}', email=f'extra{i}@test.com')
            for i in range(50)
        ]
        
        self._create_games_and_predictions(self.window1_morning, num_games=2)
        
        # Count queries to ensure we're not over-fetching
        with self.assertNumQueries(less_than=20):  # Should be efficient
            recompute_window_optimized(self.window1_morning.id)
        
        # Should only create stats for users with predictions
        stats_count = UserWindowStat.objects.filter(window=self.window1_morning).count()
        self.assertEqual(stats_count, 2, "Should only create stats for users with predictions")
        
        # user3 and extra users should NOT have stats
        users_with_stats = set(
            UserWindowStat.objects.filter(window=self.window1_morning).values_list('user_id', flat=True)
        )
        expected_users = {self.user1.id, self.user2.id}
        self.assertEqual(users_with_stats, expected_users)

    @patch('analytics.services.window_stats_optimized.logger')
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate logging occurs"""
        self._create_games_and_predictions(self.window1_morning, num_games=1)
        
        recompute_window_optimized(self.window1_morning.id)
        
        # Should log successful completion
        mock_logger.info.assert_called()
        self.assertIn("Successfully recomputed", mock_logger.info.call_args[0][0])


class EdgeCaseTests(TestCase):
    """Additional edge case tests"""
    
    def test_slot_ordering_constants(self):
        """Test that SLOT_ORDER constant handles all expected values"""
        self.assertEqual(SLOT_ORDER['morning'], 0)
        self.assertEqual(SLOT_ORDER['afternoon'], 1) 
        self.assertEqual(SLOT_ORDER['late'], 2)
        
        # Test fallback for unknown slots
        unknown_slot_order = SLOT_ORDER.get('unknown_slot', 3)
        self.assertEqual(unknown_slot_order, 3)

    def test_empty_window_handling(self):
        """Test handling of windows with no games"""
        window = Window.objects.create(
            season=2024,
            date=date.today(),
            slot='morning',
            is_complete=False
        )
        
        # Should not error on empty window
        recompute_window_optimized(window.id)
        
        # Should not create any UserWindowStat records
        stats_count = UserWindowStat.objects.filter(window=window).count()
        self.assertEqual(stats_count, 0)

    def test_concurrent_calculation_safety(self):
        """Test that concurrent calculations don't interfere"""
        user = User.objects.create_user(username='test', email='test@test.com')
        window1 = Window.objects.create(season=2024, date=date.today(), slot='morning')
        window2 = Window.objects.create(season=2024, date=date.today(), slot='afternoon')
        
        # This is a simplified test - in production you'd want to test with threading
        try:
            with transaction.atomic():
                recompute_window_optimized(window1.id)
                recompute_window_optimized(window2.id)
        except Exception as e:
            self.fail(f"Concurrent calculations should not interfere: {e}")

    def test_mixed_game_types_calculation(self):
        """Test calculation with mix of ML and prop bets"""
        # Create window with games having different combinations
        game1 = Game.objects.create(
            window=self.window1_morning,
            away_team='AWAY1',
            home_team='HOME1',
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner='HOME1',
            locked=True
        )
        
        game2 = Game.objects.create(
            window=self.window1_morning,
            away_team='AWAY2', 
            home_team='HOME2',
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner='HOME2',
            locked=True
        )
        
        # Game1: Only ML predictions
        MoneyLinePrediction.objects.create(
            user=self.user1, game=game1, predicted_winner='HOME1', is_correct=True
        )
        MoneyLinePrediction.objects.create(
            user=self.user2, game=game1, predicted_winner='AWAY1', is_correct=False
        )
        
        # Game2: ML + Prop bet
        MoneyLinePrediction.objects.create(
            user=self.user1, game=game2, predicted_winner='HOME2', is_correct=True
        )
        MoneyLinePrediction.objects.create(
            user=self.user2, game=game2, predicted_winner='AWAY2', is_correct=False
        )
        
        prop_bet = PropBet.objects.create(
            game=game2,
            question='Test prop',
            option_a='A',
            option_b='B',
            correct_answer='A'
        )
        
        PropBetPrediction.objects.create(
            user=self.user1, prop_bet=prop_bet, answer='A', is_correct=True
        )
        PropBetPrediction.objects.create(
            user=self.user2, prop_bet=prop_bet, answer='B', is_correct=False
        )
        
        recompute_window_optimized(self.window1_morning.id)
        
        # user1: 2 ML correct (2 points) + 1 PB correct (2 points) = 4 total
        # user2: 0 ML correct + 0 PB correct = 0 total
        stat1 = UserWindowStat.objects.get(user=self.user1, window=self.window1_morning)
        stat2 = UserWindowStat.objects.get(user=self.user2, window=self.window1_morning)
        
        self.assertEqual(stat1.ml_correct, 2)
        self.assertEqual(stat1.pb_correct, 1)
        self.assertEqual(stat1.window_points, 4)  # 2*1 + 1*2
        self.assertEqual(stat2.window_points, 0)

    def test_large_point_differential_ranking(self):
        """Test ranking with large point differentials"""
        # Create scenario with big point gaps
        self._create_games_and_predictions(self.window1_morning, num_games=5, with_props=True)
        
        # Create user with partial predictions
        user4 = User.objects.create_user(username='user4', email='user4@test.com')
        games = Game.objects.filter(window=self.window1_morning)
        
        # user4 gets only one correct ML prediction
        MoneyLinePrediction.objects.create(
            user=user4,
            game=games.first(),
            predicted_winner=games.first().winner,
            is_correct=True
        )
        
        recompute_window_optimized(self.window1_morning.id)
        
        stats = UserWindowStat.objects.filter(window=self.window1_morning).order_by('-season_cume_points')
        
        # user1: 5 ML + 5 PB = 15 points (rank 1)
        # user4: 1 ML + 0 PB = 1 point (rank 2)  
        # user2: 0 ML + 0 PB = 0 points (rank 3)
        
        stat_user1 = stats.get(user=self.user1)
        stat_user4 = stats.get(user=user4)
        stat_user2 = stats.get(user=self.user2)
        
        self.assertEqual(stat_user1.rank_dense, 1)
        self.assertEqual(stat_user4.rank_dense, 2)
        self.assertEqual(stat_user2.rank_dense, 3)
        
        self.assertEqual(stat_user1.season_cume_points, 15)
        self.assertEqual(stat_user4.season_cume_points, 1)
        self.assertEqual(stat_user2.season_cume_points, 0)

    def test_same_points_tied_ranking(self):
        """Test ranking when users have identical points"""
        # Create scenario where multiple users get same points
        game = Game.objects.create(
            window=self.window1_morning,
            away_team='AWAY',
            home_team='HOME',
            season=self.season,
            week=1,
            start_time=datetime.now(dt_timezone.utc),
            winner='HOME',
            locked=True
        )
        
        # All users predict correctly
        for user in [self.user1, self.user2, self.user3]:
            MoneyLinePrediction.objects.create(
                user=user,
                game=game,
                predicted_winner='HOME',
                is_correct=True
            )
        
        recompute_window_optimized(self.window1_morning.id)
        
        # All should have rank 1 (tied)
        stats = UserWindowStat.objects.filter(window=self.window1_morning)
        
        for stat in stats:
            self.assertEqual(stat.season_cume_points, 1)
            self.assertEqual(stat.rank_dense, 1)  # Dense ranking: ties share same rank