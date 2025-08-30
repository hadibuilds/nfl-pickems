/*
 * UserStatsDisplay Component
 * Fetches and displays user statistics in dropdown
 * Shows rank, accuracy, and total points
 * Now uses shared ranking utilities for consistency
 */

import React, { useState, useEffect } from 'react';
import { calculateRankWithTies } from './rankingUtils.jsx'; // Import shared utility

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
        const standingsResponse = await fetch(`${API_BASE}/analytics/api/standings/`, {
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

    // Use shared ranking utility for consistent ranking
    const userRank = calculateRankWithTies(standings, username);

    // Calculate accuracy from actual predictions data
    const accuracy = await calculateAccuracy(username);

    return {
      rank: userRank,
      accuracy: accuracy,
      totalPoints: userStanding.total_points || 0
    };
  };

  // Calculate accuracy from actual prediction data
  const calculateAccuracy = async () => {
    try {
      
      // Use the user_accuracy endpoint directly
      const accuracyResponse = await fetch(`${API_BASE}/analytics/api/user-accuracy/`, {
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });


      if (!accuracyResponse.ok) {
        return 0;
      }

      const accuracyData = await accuracyResponse.json();
      
      const overall = accuracyData?.overall_accuracy;
      if (!overall || typeof overall.percentage !== 'number') {
        return 0;
      }

      return Math.round(overall.percentage);

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
    return rank; // Just return the rank as-is (T-1, 2, 3, etc.)
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
