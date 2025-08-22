from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Max
from django.utils import timezone
from .models import (
    Prediction, PropBetPrediction, WeeklySnapshot, 
    RankHistory, UserStreak, LeaderboardSnapshot, SeasonStats
)
from games.models import Game
from collections import defaultdict

User = get_user_model()

def get_current_week():
    """
    Get the current week - the lowest week number that doesn't have all games completed
    """
    # Get all weeks that have games
    all_weeks = Game.objects.values_list('week', flat=True).distinct().order_by('week')
    
    for week in all_weeks:
        # Get all games for this week
        week_games = Game.objects.filter(week=week)
        
        # Check if ALL games in this week have winners (results)
        completed_games = week_games.filter(winner__isnull=False)
        
        # If not all games are completed, this is the current week
        if completed_games.count() < week_games.count():
            return week
    
    # If all weeks are completed, return the last week
    return all_weeks.last() if all_weeks else 1

def calculate_user_dashboard_data(user):
    """
    Calculate comprehensive dashboard data with real trends from historical data
    """
    current_week = get_current_week()
    
    # Get latest snapshot for baseline stats
    latest_snapshot = WeeklySnapshot.objects.filter(user=user).order_by('-week').first()
    
    # Get current week live stats (for pending week)
    live_stats = calculate_live_stats(user, current_week)
    
    # Get rank history for trends
    rank_history = get_user_rank_trends(user, current_week)
    
    # Get streak information
    streak_info = get_user_streak_info(user)
    
    # Get season stats
    season_stats = get_user_season_stats(user)
    
    # Calculate pending picks
    pending_picks = calculate_pending_picks(user, current_week)
    
    # Get recent games with results
    recent_games = get_recent_games_data(user, limit=3)
    
    # Get best category
    best_category, best_category_accuracy = get_best_category_with_history(user)
    
    # Combine snapshot data with live data
    if latest_snapshot:
        base_total_points = latest_snapshot.total_points
        base_overall_accuracy = latest_snapshot.overall_accuracy or 0
        base_moneyline_accuracy = latest_snapshot.moneyline_accuracy or 0
        base_prop_accuracy = latest_snapshot.prop_accuracy or 0
    else:
        base_total_points = 0
        base_overall_accuracy = 0
        base_moneyline_accuracy = 0
        base_prop_accuracy = 0
    
    # Add current week points to snapshot totals
    total_points = base_total_points + live_stats['weekly_points']
    
    return {
        'username': user.username,
        'currentWeek': current_week,
        'weeklyPoints': live_stats['weekly_points'],
        'totalPoints': total_points,
        'rank': rank_history['current_rank'],
        'rankChange': rank_history['rank_change_display'],
        'rankTrend': rank_history['trend_direction'],
        'totalUsers': rank_history['total_users'],
        'overallAccuracy': calculate_current_accuracy(user, 'overall'),
        'moneylineAccuracy': calculate_current_accuracy(user, 'moneyline'),
        'propBetAccuracy': calculate_current_accuracy(user, 'prop'),
        'streak': streak_info['current_streak'],
        'streakType': streak_info['streak_type'],
        'longestWinStreak': streak_info['longest_win_streak'],
        'longestLossStreak': streak_info['longest_loss_streak'],
        'pendingPicks': pending_picks,
        'pointsFromLeader': rank_history['points_from_leader'],
        'bestCategory': best_category,
        'bestCategoryAccuracy': best_category_accuracy,
        'recentGames': recent_games,
        'seasonStats': season_stats,
        'performanceTrend': calculate_performance_trend(user),
        'weeklyTrends': get_weekly_performance_trends(user, weeks=5)
    }

def calculate_live_stats(user, current_week):
    """Calculate stats for the current (potentially incomplete) week"""
    current_week_games = Game.objects.filter(week=current_week)
    completed_current_games = current_week_games.filter(winner__isnull=False)
    
    # Current week predictions on completed games
    week_predictions = Prediction.objects.filter(
        user=user,
        game__in=completed_current_games
    )
    game_correct = week_predictions.filter(is_correct=True).count()
    
    # Current week prop predictions on completed games
    week_props = PropBetPrediction.objects.filter(
        user=user,
        prop_bet__game__in=completed_current_games,
        is_correct__isnull=False
    )
    prop_correct = week_props.filter(is_correct=True).count()
    
    weekly_points = game_correct + (prop_correct * 2)
    
    return {
        'weekly_points': weekly_points,
        'game_correct': game_correct,
        'prop_correct': prop_correct
    }

def get_user_rank_trends(user, current_week):
    """Get rank trends using historical data"""
    # Get current rank (live calculation for current week)
    current_rank_info = calculate_current_user_rank(user, current_week)
    
    # Get rank history
    recent_rank_history = RankHistory.objects.filter(
        user=user
    ).order_by('-week')[:2]
    
    rank_change_display = "—"
    trend_direction = "same"
    
    if len(recent_rank_history) >= 1:
        latest_history = recent_rank_history[0]
        rank_change_display = latest_history.rank_change_display
        trend_direction = latest_history.trend_direction
    
    return {
        'current_rank': current_rank_info['rank'],
        'rank_change_display': rank_change_display,
        'trend_direction': trend_direction,
        'total_users': current_rank_info['total_users'],
        'points_from_leader': current_rank_info['points_from_leader']
    }

def calculate_current_user_rank(user, current_week):
    """Calculate user's current rank including live data"""
    # Get all users with their current total points
    user_points = []
    for u in User.objects.all():
        # Get latest snapshot
        latest_snapshot = WeeklySnapshot.objects.filter(user=u).order_by('-week').first()
        snapshot_points = latest_snapshot.total_points if latest_snapshot else 0
        
        # Add current week live points
        live_stats = calculate_live_stats(u, current_week)
        total_points = snapshot_points + live_stats['weekly_points']
        
        user_points.append((u.username, total_points))
    
    # Sort by points descending
    user_points.sort(key=lambda x: x[1], reverse=True)
    
    # Find user's rank
    rank = 1
    leader_points = user_points[0][1] if user_points else 0
    user_total_points = 0
    
    for i, (username, points) in enumerate(user_points):
        if username == user.username:
            rank = i + 1
            user_total_points = points
            break
    
    return {
        'rank': rank,
        'total_users': len(user_points),
        'points_from_leader': leader_points - user_total_points
    }

def get_user_streak_info(user):
    """Get streak information from UserStreak model"""
    try:
        streak = UserStreak.objects.get(user=user)
        return {
            'current_streak': streak.current_streak,
            'streak_type': streak.streak_type,
            'longest_win_streak': streak.longest_win_streak,
            'longest_loss_streak': streak.longest_loss_streak
        }
    except UserStreak.DoesNotExist:
        return {
            'current_streak': 0,
            'streak_type': 'none',
            'longest_win_streak': 0,
            'longest_loss_streak': 0
        }

def get_user_season_stats(user):
    """Get season statistics"""
    try:
        season_stats = SeasonStats.objects.get(user=user)
        return {
            'best_week_points': season_stats.best_week_points,
            'best_week_number': season_stats.best_week_number,
            'highest_rank': season_stats.highest_rank,
            'weeks_in_top_3': season_stats.weeks_in_top_3,
            'weeks_in_top_5': season_stats.weeks_in_top_5,
            'weeks_as_leader': season_stats.weeks_as_leader,
            'trending_direction': season_stats.trending_direction
        }
    except SeasonStats.DoesNotExist:
        return {
            'best_week_points': 0,
            'best_week_number': None,
            'highest_rank': None,
            'weeks_in_top_3': 0,
            'weeks_in_top_5': 0,
            'weeks_as_leader': 0,
            'trending_direction': 'stable'
        }

def calculate_current_accuracy(user, accuracy_type):
    """Calculate current accuracy including live data"""
    # Get all completed games
    completed_games = Game.objects.filter(winner__isnull=False)
    
    if accuracy_type == 'overall':
        # All predictions
        game_preds = Prediction.objects.filter(user=user, game__in=completed_games)
        prop_preds = PropBetPrediction.objects.filter(
            user=user, 
            prop_bet__game__in=completed_games,
            is_correct__isnull=False
        )
        
        correct = game_preds.filter(is_correct=True).count() + prop_preds.filter(is_correct=True).count()
        total = game_preds.count() + prop_preds.count()
        
    elif accuracy_type == 'moneyline':
        # Only game predictions
        game_preds = Prediction.objects.filter(user=user, game__in=completed_games)
        correct = game_preds.filter(is_correct=True).count()
        total = game_preds.count()
        
    elif accuracy_type == 'prop':
        # Only prop predictions
        prop_preds = PropBetPrediction.objects.filter(
            user=user,
            prop_bet__game__in=completed_games,
            is_correct__isnull=False
        )
        correct = prop_preds.filter(is_correct=True).count()
        total = prop_preds.count()
    
    return round(correct / total * 100, 1) if total > 0 else 0

def calculate_performance_trend(user):
    """Calculate if user is trending up, down, or stable based on recent weeks"""
    recent_snapshots = WeeklySnapshot.objects.filter(user=user).order_by('-week')[:4]
    
    if len(recent_snapshots) < 2:
        return 'stable'
    
    # Look at rank trends
    ranks = [snapshot.rank for snapshot in recent_snapshots]
    
    # Calculate trend (lower rank number = better)
    improving = 0
    declining = 0
    
    for i in range(len(ranks) - 1):
        if ranks[i] < ranks[i + 1]:  # Rank improved (number got smaller)
            improving += 1
        elif ranks[i] > ranks[i + 1]:  # Rank declined (number got bigger)
            declining += 1
    
    if improving > declining:
        return 'up'
    elif declining > improving:
        return 'down'
    else:
        return 'stable'

def get_weekly_performance_trends(user, weeks=5):
    """Get performance trends for the last N weeks"""
    recent_snapshots = WeeklySnapshot.objects.filter(user=user).order_by('-week')[:weeks]
    
    trends = []
    for snapshot in recent_snapshots:
        rank_history = RankHistory.objects.filter(user=user, week=snapshot.week).first()
        
        trends.append({
            'week': snapshot.week,
            'points': snapshot.weekly_points,
            'rank': snapshot.rank,
            'accuracy': snapshot.weekly_accuracy or 0,
            'rank_change': rank_history.rank_change if rank_history else 0,
            'trend': rank_history.trend_direction if rank_history else 'same'
        })
    
    return sorted(trends, key=lambda x: x['week'])

def calculate_pending_picks(user, current_week):
    """Calculate pending picks for current week (both games and prop bets)"""
    current_week_games = Game.objects.filter(week=current_week).prefetch_related('prop_bets')
    
    # Count game predictions
    user_game_predictions = Prediction.objects.filter(
        user=user, 
        game__week=current_week
    )
    games_with_predictions = set(user_game_predictions.values_list('game_id', flat=True))
    pending_games = current_week_games.exclude(id__in=games_with_predictions).count()
    
    # Count prop bet predictions
    pending_props = 0
    for game in current_week_games:
        for prop_bet in game.prop_bets.all():
            # Check if user has made this prop bet prediction
            user_prop_prediction = PropBetPrediction.objects.filter(
                user=user,
                prop_bet=prop_bet
            ).exists()
            
            if not user_prop_prediction:
                pending_props += 1
    
    # Total pending picks = pending games + pending prop bets
    total_pending = pending_games + pending_props
    
    return total_pending

def get_recent_games_data(user, limit=3):
    """Get recent completed games with user predictions"""
    recent_predictions = Prediction.objects.filter(
        user=user,
        game__winner__isnull=False
    ).select_related('game').order_by('-game__start_time')[:limit]
    
    recent_games = []
    for pred in recent_predictions:
        game = pred.game
        points = 1 if pred.is_correct else 0
        
        recent_games.append({
            'id': game.id,
            'homeTeam': game.home_team,
            'awayTeam': game.away_team,
            'userPick': pred.predicted_winner,
            'result': game.winner,
            'correct': pred.is_correct,
            'points': points
        })
    
    return recent_games

def get_best_category_with_history(user):
    """Determine user's best category using historical data"""
    # Get latest snapshot for historical context
    latest_snapshot = WeeklySnapshot.objects.filter(user=user).order_by('-week').first()
    
    if latest_snapshot:
        moneyline_accuracy = latest_snapshot.moneyline_accuracy or 0
        prop_accuracy = latest_snapshot.prop_accuracy or 0
    else:
        # Fallback to live calculation
        moneyline_accuracy = calculate_current_accuracy(user, 'moneyline')
        prop_accuracy = calculate_current_accuracy(user, 'prop')
    
    # If both are 0 (no results yet), return N/A
    if moneyline_accuracy == 0 and prop_accuracy == 0:
        return "N/A", 0
    
    # If only one has data, return that one
    if moneyline_accuracy > 0 and prop_accuracy == 0:
        return "Moneyline", moneyline_accuracy
    elif prop_accuracy > 0 and moneyline_accuracy == 0:
        return "Prop Bets", prop_accuracy
    
    # If both have data, return the better one
    if moneyline_accuracy >= prop_accuracy:
        return "Moneyline", moneyline_accuracy
    else:
        return "Prop Bets", prop_accuracy

def get_leaderboard_data_with_trends(limit=5):
    """Get leaderboard with historical trends"""
    current_week = get_current_week()
    
    # Try to get latest leaderboard snapshot
    latest_snapshot = LeaderboardSnapshot.objects.filter(week__lt=current_week).order_by('-week').first()
    
    if latest_snapshot:
        # Use snapshot data as base and calculate current positions
        leaderboard_data = latest_snapshot.snapshot_data[:limit]
        
        # Update with current live data
        for entry in leaderboard_data:
            user = User.objects.get(username=entry['username'])
            current_rank_info = calculate_current_user_rank(user, current_week)
            entry['current_rank'] = current_rank_info['rank']
            entry['current_points'] = current_rank_info['total_users'] - current_rank_info['points_from_leader']  # Leader points - gap
    else:
        # Fallback to live calculation
        leaderboard_data = []
        user_points = []
        
        for user in User.objects.all():
            latest_snapshot = WeeklySnapshot.objects.filter(user=user).order_by('-week').first()
            snapshot_points = latest_snapshot.total_points if latest_snapshot else 0
            live_stats = calculate_live_stats(user, current_week)
            total_points = snapshot_points + live_stats['weekly_points']
            
            user_points.append({
                'username': user.username,
                'points': total_points,
                'trend': 'same'  # No historical data available
            })
        
        # Sort and add ranks
        user_points.sort(key=lambda x: x['points'], reverse=True)
        for i, user_data in enumerate(user_points[:limit]):
            user_data['rank'] = i + 1
            leaderboard_data.append(user_data)
    
    return leaderboard_data

def get_user_insights(user):
    """Get personalized insights based on historical data"""
    insights = []
    
    # Get recent performance
    recent_snapshots = WeeklySnapshot.objects.filter(user=user).order_by('-week')[:3]
    
    if len(recent_snapshots) >= 2:
        latest = recent_snapshots[0]
        previous = recent_snapshots[1]
        
        # Rank improvement insight
        if latest.rank < previous.rank:
            improvement = previous.rank - latest.rank
            insights.append({
                'type': 'positive',
                'message': f"You've moved up {improvement} spots in the rankings!"
            })
        elif latest.rank > previous.rank:
            decline = latest.rank - previous.rank
            insights.append({
                'type': 'warning',
                'message': f"You've dropped {decline} spots. Time to bounce back!"
            })
    
    # Streak insights
    streak_info = get_user_streak_info(user)
    if streak_info['current_streak'] >= 3:
        streak_type = "winning" if streak_info['streak_type'] == 'win' else "losing"
        insights.append({
            'type': 'info',
            'message': f"You're on a {streak_info['current_streak']}-game {streak_type} streak!"
        })
    
    # Season stats insights
    season_stats = get_user_season_stats(user)
    if season_stats['weeks_as_leader'] > 0:
        insights.append({
            'type': 'positive',
            'message': f"You've led the league for {season_stats['weeks_as_leader']} week(s) this season!"
        })
    
    return insights