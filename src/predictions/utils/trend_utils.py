# predictions/trend_utils.py - Calculate trends without snapshots

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from ..models import Prediction, PropBetPrediction
from games.models import Game
from collections import defaultdict

User = get_user_model()

def get_completed_weeks():
    """Get list of weeks that are fully completed"""
    completed_weeks = []
    
    all_weeks = Game.objects.values_list('week', flat=True).distinct().order_by('week')
    
    for week in all_weeks:
        week_games = Game.objects.filter(week=week)
        completed_games = week_games.filter(winner__isnull=False)
        
        # Only include weeks where ALL games are completed
        if week_games.count() == completed_games.count() and week_games.count() > 0:
            completed_weeks.append(week)
    
    return completed_weeks

def calculate_user_points_by_week(user):
    """Calculate user's points for each completed week"""
    completed_weeks = get_completed_weeks()
    weekly_points = {}
    
    for week in completed_weeks:
        # Get completed games for this week
        week_games = Game.objects.filter(week=week, winner__isnull=False)
        
        # Count correct predictions for this week
        correct_game_preds = Prediction.objects.filter(
            user=user,
            game__in=week_games,
            is_correct=True
        ).count()
        
        correct_prop_preds = PropBetPrediction.objects.filter(
            user=user,
            prop_bet__game__in=week_games,
            is_correct=True
        ).count()
        
        weekly_points[week] = correct_game_preds + (correct_prop_preds * 2)
    
    return weekly_points

def calculate_user_rank_by_week(user, target_week):
    """Calculate user's rank for a specific completed week"""
    if target_week not in get_completed_weeks():
        return None
    
    # Get all users' points through this week
    user_points = []
    
    for u in User.objects.all():
        user_weekly_points = calculate_user_points_by_week(u)
        total_points = sum(points for week, points in user_weekly_points.items() if week <= target_week)
        user_points.append((u.username, total_points, u))
    
    # Sort by points descending
    user_points.sort(key=lambda x: (-x[1], x[0]))
    
    # Find user's rank
    for i, (username, points, u) in enumerate(user_points):
        if u == user:
            return i + 1
    
    return None

def get_user_rank_trend(user):
    """Calculate rank change from last completed week to second-to-last"""
    completed_weeks = get_completed_weeks()
    
    if len(completed_weeks) < 2:
        return "—", "same"
    
    # Get last two completed weeks
    current_week = completed_weeks[-1]
    previous_week = completed_weeks[-2]
    
    current_rank = calculate_user_rank_by_week(user, current_week)
    previous_rank = calculate_user_rank_by_week(user, previous_week)
    
    if current_rank is None or previous_rank is None:
        return "—", "same"
    
    # Calculate change (positive = moved up, negative = moved down)
    rank_change = previous_rank - current_rank
    
    if rank_change > 0:
        return f"+{rank_change}", "up"
    elif rank_change < 0:
        return str(rank_change), "down"
    else:
        return "—", "same"

def get_user_performance_trend(user):
    """Determine if user is trending up/down based on recent weeks"""
    completed_weeks = get_completed_weeks()
    
    if len(completed_weeks) < 3:
        return "stable"
    
    # Get last 3 weeks of ranks
    recent_ranks = []
    for week in completed_weeks[-3:]:
        rank = calculate_user_rank_by_week(user, week)
        if rank:
            recent_ranks.append(rank)
    
    if len(recent_ranks) < 3:
        return "stable"
    
    # Check trend (lower rank numbers = better)
    improving = 0
    declining = 0
    
    for i in range(len(recent_ranks) - 1):
        if recent_ranks[i] > recent_ranks[i + 1]:  # Rank improved
            improving += 1
        elif recent_ranks[i] < recent_ranks[i + 1]:  # Rank declined
            declining += 1
    
    if improving > declining:
        return "up"
    elif declining > improving:
        return "down"
    else:
        return "stable"

def get_user_weekly_insights(user):
    """Generate insights based on recent performance"""
    insights = []
    
    # Rank change insight
    rank_change, trend = get_user_rank_trend(user)
    if trend == "up" and rank_change != "—":
        insights.append({
            'type': 'positive',
            'message': f"You moved up {rank_change.replace('+', '')} spots this week!"
        })
    elif trend == "down" and rank_change != "—":
        insights.append({
            'type': 'warning', 
            'message': f"You dropped {rank_change.replace('-', '')} spots this week."
        })
    
    # Performance trend insight
    performance_trend = get_user_performance_trend(user)
    if performance_trend == "up":
        insights.append({
            'type': 'positive',
            'message': "You're on an upward trend over the last few weeks!"
        })
    elif performance_trend == "down":
        insights.append({
            'type': 'info',
            'message': "Time to turn things around - you can do it!"
        })
    
    return insights