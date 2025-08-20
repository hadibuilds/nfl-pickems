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
        const userStats = calculateUserStats(standingsData.standings, userInfo.username);
        
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
  const calculateUserStats = (standings, username) => {
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

    // Calculate rank (position in sorted standings)
    const sortedStandings = [...standings].sort((a, b) => b.total_points - a.total_points);
    const userRank = sortedStandings.findIndex(standing => 
      standing.username.toLowerCase() === username.toLowerCase()
    ) + 1;

    // Calculate accuracy (this would need prediction data - placeholder for now)
    // TODO: Implement actual accuracy calculation from predictions API
    const accuracy = calculateAccuracy(userStanding);

    return {
      rank: userRank,
      accuracy: accuracy,
      totalPoints: userStanding.total_points || 0
    };
  };

  // Placeholder accuracy calculation - implement with actual prediction data
  const calculateAccuracy = (userStanding) => {
    // TODO: Fetch user's predictions and calculate win percentage
    // For now, simulate based on total points (rough estimate)
    const points = userStanding.total_points || 0;
    const estimatedGames = Math.max(points / 1.5, 1); // Rough estimate
    const accuracy = Math.min((points / estimatedGames) * 100, 100);
    return Math.round(accuracy);
  };

  // Helper function to get CSRF token
  const getCookie = (name) => {
    const cookie = document.cookie
      .split('; ')
      .find(row => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };

  // Format rank display
  const formatRank = (rank) => {
    if (rank === '—' || rank === null) return '—';
    return `#${rank}`;
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