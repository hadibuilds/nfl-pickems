// hooks/useDashboardData.js - Original version without caching
import { useState, useEffect } from 'react';

const useDashboardData = (userInfo, options = {}) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingStates, setLoadingStates] = useState({
    stats: true,
    accuracy: true,
    leaderboard: true,
    recent: true,
    insights: true
  });

  // Get API base URL from environment or use default
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // Options for what to load
  const {
    loadFull = false,
    loadGranular = true,
    includeLeaderboard = true,
    sections = null
  } = options;

  const getCsrfToken = () => {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
  };

  const fetchFullDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const url = sections 
        ? `${API_BASE}/predictions/api/dashboard/?sections=${sections.join(',')}`
        : `${API_BASE}/predictions/api/dashboard/`;

      const response = await fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Dashboard data calculation mode:', data.meta?.calculation_mode);
      
      setDashboardData(data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchGranularDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Initialize with proper structure that matches Django response
      setDashboardData({
        user_data: {},
        leaderboard: [],
        insights: []
      });

      const promises = [];

      // FAST: Load user stats first (shows immediately)
      const statsPromise = fetch(`${API_BASE}/predictions/api/dashboard/stats/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() }
      }).then(res => res.json()).then(data => {
        setLoadingStates(prev => ({ ...prev, stats: false }));
        // Update dashboard with stats data
        setDashboardData(prev => ({
          ...prev,
          user_data: { ...prev?.user_data, ...data }
        }));
        return data;
      });

      promises.push(statsPromise);

      // FAST: Load accuracy data
      const accuracyPromise = fetch(`${API_BASE}/predictions/api/dashboard/accuracy/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() }
      }).then(res => res.json()).then(data => {
        setLoadingStates(prev => ({ ...prev, accuracy: false }));
        // Update dashboard with accuracy data - careful merging
        setDashboardData(prev => ({
          ...prev,
          user_data: { 
            ...prev?.user_data, 
            overallAccuracy: data.overallAccuracy,
            moneylineAccuracy: data.moneylineAccuracy,
            propBetAccuracy: data.propBetAccuracy,
            bestCategory: data.bestCategory,
            bestCategoryAccuracy: data.bestCategoryAccuracy,
            totalPoints: data.totalPoints
          }
        }));
        return data;
      });

      promises.push(accuracyPromise);

      // MEDIUM: Load leaderboard (only if needed)
      if (includeLeaderboard) {
        const leaderboardPromise = fetch(`${API_BASE}/predictions/api/dashboard/leaderboard/?limit=5`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCsrfToken() }
        }).then(res => res.json()).then(data => {
          setLoadingStates(prev => ({ ...prev, leaderboard: false }));
          // Update dashboard with leaderboard
          setDashboardData(prev => ({ ...prev, leaderboard: data.leaderboard }));
          return data;
        });

        promises.push(leaderboardPromise);
      } else {
        setLoadingStates(prev => ({ ...prev, leaderboard: false }));
      }

      // FAST: Load recent games
      const recentPromise = fetch(`${API_BASE}/predictions/api/dashboard/recent/?limit=3`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() }
      }).then(res => res.json()).then(data => {
        setLoadingStates(prev => ({ ...prev, recent: false }));
        // Update dashboard with recent games
        setDashboardData(prev => ({
          ...prev,
          user_data: { ...prev?.user_data, recentGames: data.recentGames }
        }));
        return data;
      });

      promises.push(recentPromise);

      // FAST: Load insights
      const insightsPromise = fetch(`${API_BASE}/predictions/api/dashboard/insights/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() }
      }).then(res => res.json()).then(data => {
        setLoadingStates(prev => ({ ...prev, insights: false }));
        // Update dashboard with insights
        setDashboardData(prev => ({
          ...prev,
          insights: data.insights,
          user_data: {
            ...prev?.user_data,
            streak: data.streak,
            streakType: data.streakType,
            longestWinStreak: data.longestWinStreak,
            longestLossStreak: data.longestLossStreak,
            seasonStats: data.seasonStats
          }
        }));
        return data;
      });

      promises.push(insightsPromise);

      // Wait for all requests to complete
      await Promise.all(promises);

      console.log('All granular dashboard data loaded');
      
    } catch (err) {
      console.error('Error fetching granular dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDashboardData = loadFull ? fetchFullDashboard : fetchGranularDashboard;

  useEffect(() => {
    if (!userInfo?.username) return;
    fetchDashboardData();
  }, [userInfo?.username, API_BASE, loadFull, loadGranular, includeLeaderboard]);

  return { 
    dashboardData, 
    loading, 
    error, 
    loadingStates,
    refetch: fetchDashboardData,
    isRealtime: dashboardData?.meta?.calculation_mode === 'realtime'
  };
};

export default useDashboardData;