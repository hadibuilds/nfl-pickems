def get_season_leaderboard_fast(through_week=None, limit=20):
    """
    Super fast season leaderboard using the latest UserStatHistory snapshots.
    """
    if through_week is None:
        through_week = get_current_week()
    
    # Get the latest snapshot for each user through the specified week
    latest_snapshots = []
    for user in User.objects.all():
        stats = UserStatHistory.objects.filter(
            user=user,
            week__lte=through_week
        ).order_by('-week').first()
        
        if stats:
            latest_snapshots.append({
                'username': user.username,
                'rank': stats.rank,
                'total_points': stats.total_points,
                'season_accuracy': stats.season_accuracy,
                'moneyline_accuracy': stats.moneyline_accuracy,
                'prop_accuracy': stats.prop_accuracy,
                'trend': stats.trend_direction,
                'rank_change': stats.rank_change,
                'last_updated_week': stats.week,
                'week_points': stats.week_points,
            })
    
    # Sort by total points (descending), then username (ascending) for tiebreakers
    latest_snapshots.sort(key=lambda x: (-x['total_points'], x['username']))
    
    # Update ranks (in case we're looking at historical data)
    for i, entry in enumerate(latest_snapshots[:limit]):
        entry['current_rank'] = i + 1
    
    return latest_snapshots[:limit]


def get_weekly_insights_fast(user):
    """
    Generate insights using UserStatHistory snapshot data for speed.
    """
    insights = []
    
    # Get recent snapshots
    recent_snapshots = UserStatHistory.objects.filter(user=user).order_by('-week')[:4]
    
    if len(recent_snapshots) >= 2:
        latest = recent_snapshots[0]
        previous = recent_snapshots[1]
        
        # Rank movement insights
        if latest.rank < previous.rank:
            improvement = previous.rank - latest.rank
            insights.append({
                'type': 'positive',
                'message': f"You climbed {improvement} spots to #{latest.rank} this week!"
            })
        elif latest.rank > previous.rank:
            decline = latest.rank - previous.rank
            insights.append({
                'type': 'warning',
                'message': f"You dropped {decline} spots to #{latest.rank} this week."
            })
        
        # Performance insights
        if latest.week_accuracy > 80:
            insights.append({
                'type': 'positive',
                'message': f"Excellent {latest.week_accuracy}% accuracy this week!"
            })
        elif latest.week_accuracy < 40:
            insights.append({
                'type': 'warning',
                'message': f"Tough week with {latest.week_accuracy}% accuracy. Bounce back next week!"
            })
        
        # Points performance
        if latest.week_points > previous.week_points:
            improvement = latest.week_points - previous.week_points
            insights.append({
                'type': 'positive',
                'message': f"Great improvement! +{improvement} more points than last week!"
            })
    
    # Season-level insights
    if len(recent_snapshots) >= 1:
        latest = recent_snapshots[0]
        
        if latest.season_accuracy > 65:
            insights.append({
                'type': 'positive',
                'message': f"Outstanding {latest.season_accuracy}% season accuracy!"
            })
        elif latest.season_accuracy > 55:
            insights.append({
                'type': 'positive', 
                'message': f"Solid {latest.season_accuracy}% season accuracy overall!"
            })
        
        # Check for consistency - 3+ strong weeks
        if len(recent_snapshots) >= 3:
            recent_weeks_points = [s.week_points for s in recent_snapshots[:3]]
            avg_points = sum(recent_weeks_points) / len(recent_weeks_points)
            if avg_points >= 8:  # Adjust threshold as needed
                insights.append({
                    'type': 'positive',
                    'message': f"On fire! Averaging {avg_points:.1f} points over 3 weeks!"
                })
        
        # Category strength insights
        if latest.moneyline_accuracy > latest.prop_accuracy + 15:
            insights.append({
                'type': 'info',
                'message': f"Moneyline specialist! {latest.moneyline_accuracy}% vs {latest.prop_accuracy}% on props."
            })
        elif latest.prop_accuracy > latest.moneyline_accuracy + 15:
            insights.append({
                'type': 'info', 
                'message': f"Prop bet expert! {latest.prop_accuracy}% vs {latest.moneyline_accuracy}% on games."
            })
        
        # Leadership insights
        if latest.rank == 1:
            insights.append({
                'type': 'positive',
                'message': "👑 You're leading the league! Keep it up!"
            })
        elif latest.rank <= 3:
            insights.append({
                'type': 'positive',
                'message': f"🏆 Top 3 finish! You're #{latest.rank} in the league!"
            })
    
    return insights


def get_user_week_breakdown_fast(user, week):
    """
    Get detailed breakdown of a specific week using UserStatHistory.
    """
    stats = UserStatHistory.objects.filter(user=user, week=week).first()
    
    if not stats:
        return None
    
    return {
        'week': week,
        'rank': stats.rank,
        'previous_rank': stats.previous_rank,
        'rank_change': stats.rank_change,
        'trend': stats.trend_direction,
        
        'points': {
            'week_total': stats.week_points,
            'season_total': stats.total_points,
        },
        
        'week_performance': {
            'moneyline_correct': stats.week_moneyline_correct,
            'moneyline_total': stats.week_moneyline_total,
            'prop_correct': stats.week_prop_correct,
            'prop_total': stats.week_prop_total,
            'accuracy': stats.week_accuracy,
        },
        
        'season_performance': {
            'moneyline_correct': stats.season_moneyline_correct,
            'moneyline_total': stats.season_moneyline_total,
            'prop_correct': stats.season_prop_correct,
            'prop_total': stats.season_prop_total,
            'season_accuracy': stats.season_accuracy,
            'moneyline_accuracy': stats.moneyline_accuracy,
            'prop_accuracy': stats.prop_accuracy,
        }
    }


def get_top_performers_by_category_fast(week=None, limit=5):
    """
    Get top performers in different categories using UserStatHistory.
    """
    if week:
        # Specific week performance
        week_stats = UserStatHistory.objects.filter(week=week)
    else:
        # Latest week performance
        latest_week = UserStatHistory.objects.aggregate(max_week=models.Max('week'))['max_week']
        if not latest_week:
            return {}
        week_stats = UserStatHistory.objects.filter(week=latest_week)
    
    if not week_stats.exists():
        return {}
    
    return {
        'most_points': list(week_stats.order_by('-week_points')[:limit].values(
            'user__username', 'week_points', 'rank'
        )),
        'best_accuracy': list(week_stats.filter(
            week_predictions_total__gte=5  # Minimum predictions required
        ).order_by('-week_accuracy')[:limit].values(
            'user__username', 'week_accuracy', 'week_points'
        )),
        'best_moneyline': list(week_stats.filter(
            week_moneyline_total__gte=3
        ).order_by('-moneyline_accuracy')[:limit].values(
            'user__username', 'moneyline_accuracy', 'week_moneyline_correct', 'week_moneyline_total'
        )),
        'best_props': list(week_stats.filter(
            week_prop_total__gte=2
        ).order_by('-prop_accuracy')[:limit].values(
            'user__username', 'prop_accuracy', 'week_prop_correct', 'week_prop_total'
        )),
        'biggest_climbers': list(week_stats.filter(
            rank_change__gt=0
        ).order_by('-rank_change')[:limit].values(
            'user__username', 'rank_change', 'rank', 'previous_rank'
        )),
    }


def get_historical_matchup_fast(user1, user2, weeks_back=10):
    """
    Compare two users head-to-head over recent weeks using UserStatHistory.
    """
    # Get recent stats for both users
    user1_stats = UserStatHistory.objects.filter(user=user1).order_by('-week')[:weeks_back]
    user2_stats = UserStatHistory.objects.filter(user=user2).order_by('-week')[:weeks_back]
    
    if not user1_stats or not user2_stats:
        return None
    
    # Create week-by-week comparison
    comparison_weeks = []
    user1_wins = 0
    user2_wins = 0
    
    for week in range(weeks_back):
        if week < len(user1_stats) and week < len(user2_stats):
            u1_stat = user1_stats[week]
            u2_stat = user2_stats[week]
            
            if u1_stat.week == u2_stat.week:  # Same week
                week_winner = user1.username if u1_stat.week_points > u2_stat.week_points else user2.username
                if u1_stat.week_points > u2_stat.week_points:
                    user1_wins += 1
                elif u2_stat.week_points > u1_stat.week_points:
                    user2_wins += 1
                
                comparison_weeks.append({
                    'week': u1_stat.week,
                    'user1_points': u1_stat.week_points,
                    'user2_points': u2_stat.week_points,
                    'user1_rank': u1_stat.rank,
                    'user2_rank': u2_stat.rank,
                    'winner': week_winner,
                    'point_difference': abs(u1_stat.week_points - u2_stat.week_points),
                })
    
    return {
        'user1': user1.username,
        'user2': user2.username,
        'user1_wins': user1_wins,
        'user2_wins': user2_wins,
        'ties': len(comparison_weeks) - user1_wins - user2_wins,
        'weeks_compared': len(comparison_weeks),
        'head_to_head_leader': user1.username if user1_wins > user2_wins else user2.username if user2_wins > user1_wins else 'Tied',
        'weekly_breakdown': comparison_weeks,
    }# Add these super-fast functions to dashboard_utils.py

def get_user_season_stats_fast(user, through_week=None):
    """
    Ultra-fast season statistics using UserStatHistory snapshots.
    Falls back to realtime calculation if snapshots unavailable.
    """
    if through_week is None:
        through_week = get_current_week()
    
    # Get the latest snapshot for this user up to the specified week
    latest_snapshot = UserStatHistory.objects.filter(
        user=user, 
        week__lte=through_week
    ).order_by('-week').first()
    
    if not latest_snapshot:
        # Fallback to current method if no snapshots exist
        return get_user_season_stats(user)
    
    # Calculate additional stats from all snapshots
    all_snapshots = UserStatHistory.objects.filter(
        user=user,
        week__lte=through_week
    ).order_by('week')
    
    if not all_snapshots.exists():
        return get_user_season_stats(user)
    
    # Find best week and highest rank
    best_week = max(all_snapshots, key=lambda s: s.week_points)
    highest_rank_snapshot = min(all_snapshots, key=lambda s: s.rank)
    
    # Count weeks in top positions
    weeks_in_top_3 = all_snapshots.filter(rank__lte=3).count()
    weeks_in_top_5 = all_snapshots.filter(rank__lte=5).count()
    weeks_as_leader = all_snapshots.filter(rank=1).count()
    
    return {
        'best_week_points': best_week.week_points,
        'best_week_number': best_week.week,
        'highest_rank': highest_rank_snapshot.rank,
        'highest_rank_week': highest_rank_snapshot.week,
        'weeks_in_top_3': weeks_in_top_3,
        'weeks_in_top_5': weeks_in_top_5,
        'weeks_as_leader': weeks_as_leader,
        'current_season_points': latest_snapshot.total_points,
        'current_season_accuracy': latest_snapshot.season_accuracy,
        'current_moneyline_accuracy': latest_snapshot.moneyline_accuracy,
        'current_prop_accuracy': latest_snapshot.prop_accuracy,
        'trending_direction': latest_snapshot.trend_direction,
    }


def get_user_weekly_trends_fast(user, weeks=5):
    """
    Get weekly performance trends using UserStatHistory snapshots (super fast).
    """
    snapshots = UserStatHistory.objects.filter(user=user).order_by('-week')[:weeks]
    
    trends = []
    for snapshot in reversed(snapshots):  # Reverse to get chronological order
        trends.append({
            'week': snapshot.week,
            'points': snapshot.week_points,
            'rank': snapshot.rank,
            'rank_change': snapshot.rank_change,
            'trend': snapshot.trend_direction,
            'accuracy': snapshot.week_accuracy,
            'total_points': snapshot.total_points,
            'moneyline_accuracy': snapshot.moneyline_accuracy,
            'prop_accuracy': snapshot.prop_accuracy,
        })
    
    return trends


def get_leaderboard_history_fast(week, limit=10):
    """
    Get historical leaderboard for a specific week using snapshots.
    """
    # First try to get from LeaderboardSnapshot
    snapshot = LeaderboardSnapshot.objects.filter(week=week).first()
    if snapshot and snapshot.snapshot_data:
        return snapshot.snapshot_data[:limit]
    
    # Fallback: reconstruct from UserStatHistory
    stat_entries = UserStatHistory.objects.filter(week=week).order_by('rank')[:limit]
    return [
        {
            'rank': entry.rank,
            'username': entry.user.username,
            'points': entry.total_points,
            'week_points': entry.week_points,
            'rank_change': entry.rank_change,
            'accuracy': entry.season_accuracy,
        }
        for entry in stat_entries
    ]


def compare_users_season_performance(user1, user2, through_week=None):
    """
    Fast comparison between two users using UserStatHistory snapshots.
    """
    if through_week is None:
        through_week = get_current_week()
    
    # Get latest snapshots for both users
    user1_stats = UserStatHistory.objects.filter(
        user=user1, week__lte=through_week
    ).order_by('-week').first()
    
    user2_stats = UserStatHistory.objects.filter(
        user=user2, week__lte=through_week
    ).order_by('-week').first()
    
    if not user1_stats or not user2_stats:
        return None
    
    return {
        'user1': {
            'username': user1.username,
            'rank': user1_stats.rank,
            'total_points': user1_stats.total_points,
            'season_accuracy': user1_stats.season_accuracy,
            'moneyline_accuracy': user1_stats.moneyline_accuracy,
            'prop_accuracy': user1_stats.prop_accuracy,
            'trend': user1_stats.trend_direction,
        },
        'user2': {
            'username': user2.username,
            'rank': user2_stats.rank,
            'total_points': user2_stats.total_points,
            'season_accuracy': user2_stats.season_accuracy,
            'moneyline_accuracy': user2_stats.moneyline_accuracy,
            'prop_accuracy': user2_stats.prop_accuracy,
            'trend': user2_stats.trend_direction,
        },
        'comparison': {
            'point_difference': user1_stats.total_points - user2_stats.total_points,
            'rank_difference': user2_stats.rank - user1_stats.rank,  # Lower rank is better
            'accuracy_difference': user1_stats.season_accuracy - user2_stats.season_accuracy,
            'leader': user1.username if user1_stats.total_points > user2_stats.total_points else user2.username,
        }
    }


def get_season_leaderboard_fast(through_week=None, limit=20):
    """
    Super fast season leaderboard using the latest snapshots.
    """
    if through_week is None:
        through_week = get_current_week()
    
    # Get the latest snapshot for each user through the specified week
    latest_snapshots = []
    for user in User.objects.all():
        snapshot = RankHistory.objects.filter(
            user=user,
            week__lte=through_week
        ).order_by('-week').first()
        
        if snapshot:
            latest_snapshots.append({
                'username': user.username,
                'rank': snapshot.rank,
                'total_points': snapshot.total_points,
                'season_accuracy': snapshot.season_accuracy,
                'trend': snapshot.trend_direction,
                'rank_change': snapshot.rank_change,
                'last_updated_week': snapshot.week,
            })
    
    # Sort by total points
    latest_snapshots.sort(key=lambda x: (-x['total_points'], x['username']))
    
    # Update ranks (in case we're looking at historical data)
    for i, entry in enumerate(latest_snapshots[:limit]):
        entry['current_rank'] = i + 1
    
    return latest_snapshots[:limit]


def get_weekly_insights_fast(user):
    """
    Generate insights using snapshot data for speed.
    """
    insights = []
    
    # Get recent snapshots
    recent_snapshots = RankHistory.objects.filter(user=user).order_by('-week')[:4]
    
    if len(recent_snapshots) >= 2:
        latest = recent_snapshots[0]
        previous = recent_snapshots[1]
        
        # Rank movement insights
        if latest.rank < previous.rank:
            improvement = previous.rank - latest.rank
            insights.append({
                'type': 'positive',
                'message': f"You climbed {improvement} spots to #{latest.rank} this week!"
            })
        elif latest.rank > previous.rank:
            decline = latest.rank - previous.rank
            insights.append({
                'type': 'warning',
                'message': f"You dropped {decline} spots to #{latest.rank} this week."
            })
        
        # Performance insights
        if latest.week_accuracy > 80:
            insights.append({
                'type': 'positive',
                'message': f"Excellent {latest.week_accuracy}% accuracy this week!"
            })
        elif latest.week_accuracy < 40:
            insights.append({
                'type': 'warning',
                'message': f"Tough week with {latest.week_accuracy}% accuracy. Bounce back next week!"
            })
    
    # Season-level insights
    if len(recent_snapshots) >= 1:
        latest = recent_snapshots[0]
        
        if latest.season_accuracy > 60:
            insights.append({
                'type': 'positive',
                'message': f"Strong {latest.season_accuracy}% season accuracy overall!"
            })
        
        # Check for consistency
        if len(recent_snapshots) >= 3:
            recent_weeks_points = [s.week_points for s in recent_snapshots[:3]]
            if all(points >= 8 for points in recent_weeks_points):  # Assuming 8+ is good
                insights.append({
                    'type': 'positive',
                    'message': "You're on fire! 3 strong weeks in a row!"
                })
    
    return insights