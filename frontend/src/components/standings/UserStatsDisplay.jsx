/*
 * UserStatsDisplay Component
 * Fetches and displays user statistics in dropdown
 * Shows rank, accuracy, and total points
 */

import React, { useState, useEffect } from 'react';

export default function UserStatsDisplay({ userInfo }) {
  const [stats, setStats] = useState({
    rank: null,
    accuracy: null,
    totalPoints: null,
    isLoading: true
  });

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!userInfo?.username) return;

    const fetchUserStats = async () => {
      try {
        setStats(prev => ({ ...prev, isLoading: true }));

        // Fetch standings data to calculate user stats
        const standingsResponse = await fetch(`${API_BASE}/predictions/api/standings/`, {
          credentials: 'include',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          },
        });

        if (!standingsResponse.ok) throw new Error('Failed to fetch standings');
        
        const standingsData = await standingsResponse.json();
        const userStats = await calculateUserStats(standingsData.standings, userInfo.username);
        
        setStats({
          ...userStats,
          isLoading: false
        });

      } catch (error) {
        console.error('Error fetching user stats:', error);
        setStats({
          rank: '—',
          accuracy: '—',
          totalPoints: '—',
          isLoading: false
        });
      }
    };

    fetchUserStats();
  }, [userInfo?.username, API_BASE]);

  // Calculate user statistics from standings data
  const calculateUserStats = async (standings, username) => {
    // Find user in standings
    const userStanding = standings.find(standing => 
      standing.username.toLowerCase() === username.toLowerCase()
    );

    if (!userStanding) {
      return {
        rank: '—',
        accuracy: '—', 
        totalPoints: '—'
      };
    }

    // Calculate rank with proper tie handling
    const sortedStandings = [...standings].sort((a, b) => b.total_points - a.total_points);
    const userRank = calculateRankWithTies(sortedStandings, username);

    // Calculate accuracy from actual predictions data (await the async function)
    const accuracy = await calculateAccuracy(username);

    return {
      rank: userRank,
      accuracy: accuracy,
      totalPoints: userStanding.total_points || 0
    };
  };

  // Calculate rank with tie handling (T1, T2, etc.)
  const calculateRankWithTies = (sortedStandings, username) => {
    const userStanding = sortedStandings.find(standing => 
      standing.username.toLowerCase() === username.toLowerCase()
    );
    
    if (!userStanding) return '—';

    const userPoints = userStanding.total_points || 0;
    let rank = 1;
    let currentRank = 1;
    
    for (let i = 0; i < sortedStandings.length; i++) {
      const standing = sortedStandings[i];
      const points = standing.total_points || 0;
      
      // If this is not the first person and points are different, update rank
      if (i > 0 && points !== (sortedStandings[i-1].total_points || 0)) {
        currentRank = i + 1;
      }
      
      if (standing.username.toLowerCase() === username.toLowerCase()) {
        // Check if there are ties
        const playersWithSamePoints = sortedStandings.filter(s => 
          (s.total_points || 0) === userPoints
        );
        
        if (playersWithSamePoints.length > 1) {
          return `T${currentRank}`;
        } else {
          return currentRank;
        }
      }
    }
    
    return '—';
  };

  // Calculate accuracy from actual prediction data
  const calculateAccuracy = async (username) => {
    try {
      console.log('🎯 Calculating accuracy for:', username);
      
      // Use the user_accuracy endpoint directly
      const accuracyResponse = await fetch(`${API_BASE}/predictions/api/user-accuracy/`, {
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });

      console.log('📊 User accuracy API response:', accuracyResponse.status, accuracyResponse.statusText);

      if (!accuracyResponse.ok) {
        console.warn('❌ User accuracy endpoint failed:', accuracyResponse.status);
        return 0;
      }

      const accuracyData = await accuracyResponse.json();
      console.log('✅ User accuracy data:', accuracyData);
      
      const { correct_predictions, total_predictions_with_results } = accuracyData;

      if (total_predictions_with_results === 0) {
        console.log('📝 No predictions with results yet');
        return 0;
      }

      // Calculate accuracy percentage
      const accuracy = (correct_predictions / total_predictions_with_results) * 100;
      console.log(`🎯 Calculated accuracy: ${correct_predictions}/${total_predictions_with_results} = ${accuracy}%`);
      
      return Math.round(accuracy);

    } catch (error) {
      console.error('❌ Error calculating accuracy:', error);
      return 0;
    }
  };

  // Helper function to get CSRF token
  const getCookie = (name) => {
    const cookie = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };

  // Format rank display (remove # symbol)
  const formatRank = (rank) => {
    if (rank === '—' || rank === null) return '—';
    return rank; // Just return the rank as-is (T1, T2, 3, 4, etc.)
  };

  // Format accuracy display
  const formatAccuracy = (accuracy) => {
    if (accuracy === '—' || accuracy === null) return '—';
    return `${accuracy}%`;
  };

  if (stats.isLoading) {
    return (
      <div className="dropdown-stats">
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-value loading">—</span>
            <span className="stat-label">Rank</span>
          </div>
          <div className="stat-item">
            <span className="stat-value loading">—</span>
            <span className="stat-label">Accuracy</span>
          </div>
          <div className="stat-item">
            <span className="stat-value loading">—</span>
            <span className="stat-label">Points</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dropdown-stats">
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-value">{formatRank(stats.rank)}</span>
          <span className="stat-label">Rank</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{formatAccuracy(stats.accuracy)}</span>
          <span className="stat-label">Accuracy</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.totalPoints}</span>
          <span className="stat-label">Points</span>
        </div>
      </div>
    </div>
  );
}