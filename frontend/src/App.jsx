/*
 * Main App Component - PERFORMANCE OPTIMIZED
 * Uses useMemo and useCallback to prevent unnecessary re-renders
 * Memoizes expensive operations like sorting and date calculations
 * FIXED: Prevents recreating objects/functions on every render
 */

import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import './App.css';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import WeekPage from './pages/WeekPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import Standings from './pages/Standings';
import WeekSelector from "./pages/WeekSelector"; 
import PrivateRoute from './components/PrivateRoute';
import { useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { getCookie } from './utils/cookies';
import { useLocation } from 'react-router-dom';

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

export default function App() {
  const { userInfo, isLoading } = useAuth();
  const [games, setGames] = useState([]);
  const [moneyLineSelections, setMoneyLineSelections] = useState({});
  const [propBetSelections, setPropBetSelections] = useState({});
  const [gameResults, setGameResults] = useState({});
  const [isOpen, setIsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [touchStartX, setTouchStartX] = useState(0);
  const [touchEndX, setTouchEndX] = useState(0);

  const API_BASE = import.meta.env.VITE_API_URL;

  // ✅ OPTIMIZED: Memoize data fetching functions to prevent recreation
  const fetchGameData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/games/api/games/`, {
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });
      if (!res.ok) throw new Error('Failed to fetch games');
      const data = await res.json();
      setGames(data);
    } catch (err) {
      console.error('Error fetching games:', err);
      setGames([]);
    }
  }, [API_BASE]);

  const fetchUserPredictions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/predictions/api/get-user-predictions/`, {
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });
      if (!res.ok) throw new Error('Failed to fetch predictions');
      const data = await res.json();

      const moneyLine = data.predictions.reduce((acc, cur) => {
        acc[cur.game_id] = cur.predicted_winner;
        return acc;
      }, {});
      const propBets = data.prop_bets.reduce((acc, cur) => {
        acc[cur.prop_bet_id] = cur.answer;
        return acc;
      }, {});

      setMoneyLineSelections(moneyLine);
      setPropBetSelections(propBets);
    } catch (err) {
      console.error('Error fetching predictions:', err);
      setMoneyLineSelections({});
      setPropBetSelections({});
    }
  }, [API_BASE]);

  const fetchGameResults = useCallback(async () => {
    try {
      console.log('🔄 Fetching game results...');
      const res = await fetch(`${API_BASE}/predictions/api/game-results/`, {
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });
      if (!res.ok) throw new Error('Failed to fetch game results');
      const data = await res.json();
      
      console.log('📊 Raw game results from API:', data);
      
      // Transform the results into the expected format
      const resultsMap = {};
      data.forEach(result => {
        resultsMap[result.game_id] = {
          winner: result.winning_team,
          prop_result: result.prop_bet_result
        };
      });
      
      console.log('🎯 Transformed results map:', resultsMap);
      setGameResults(resultsMap);
    } catch (err) {
      console.error('Error fetching game results:', err);
      setGameResults({});
    }
  }, [API_BASE]);

  // ✅ OPTIMIZED: Memoize refresh function to prevent recreation
  const refreshAllData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        fetchGameData(),
        fetchUserPredictions(),
        fetchGameResults()
      ]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchGameData, fetchUserPredictions, fetchGameResults]);

  // ✅ OPTIMIZED: Memoize handlers to prevent recreation on every render
  const handleMoneyLineClick = useCallback(async (game, team) => {
    if (game.locked) return;

    try {
      const res = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ game_id: game.id, predicted_winner: team }),
        credentials: 'include',
      });
    
      const data = await res.json();
    
      if (!res.ok) {
        throw new Error(data.message || `HTTP error! status: ${res.status}`);
      }
    
      if (data.success) {
        // Use functional state update to prevent race conditions
        setMoneyLineSelections(prev => ({ ...prev, [game.id]: team }));
        return data;
      } else {
        throw new Error(data.message || 'Save failed');
      }
    } catch (err) {
      console.error("Failed to save moneyline selection:", err);
      throw err;
    }
  }, [API_BASE]);

  const handlePropBetClick = useCallback(async (game, answer) => {
    if (game.locked) return;
    const propBetId = game.prop_bets?.[0]?.id;
    if (!propBetId) return;

    try {
      const res = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ prop_bet_id: propBetId, answer }),
        credentials: 'include',
      });
    
      const data = await res.json();
    
      if (!res.ok) {
        throw new Error(data.message || `HTTP error! status: ${res.status}`);
      }
    
      if (data.success) {
        // Use functional state update to prevent race conditions
        setPropBetSelections(prev => ({ ...prev, [propBetId]: answer }));
        return data;
      } else {
        throw new Error(data.message || 'Save failed');
      }
    } catch (err) {
      console.error("Failed to save prop bet selection:", err);
      throw err;
    } 
  }, [API_BASE]);

  // ✅ HUGE OPTIMIZATION: Memoize sortedGames to prevent recreation on every render
  const sortedGames = useMemo(() => {
    if (!Array.isArray(games)) return [];
    
    console.log('🔄 Recalculating sortedGames (should only happen when games change)');
    
    // Pre-calculate dates to avoid repeated Date parsing
    const gamesWithDates = games.map(game => ({
      ...game,
      _sortDate: new Date(game.start_time).getTime() // Cache parsed date as timestamp
    }));
    
    return gamesWithDates.sort((a, b) => a._sortDate - b._sortDate);
  }, [games]); // Only recalculate when games array actually changes

  // ✅ OPTIMIZED: Memoize touch handlers
  const handleTouchStart = useCallback((e) => {
    setTouchStartX(e.targetTouches[0].clientX);
  }, []);
    
  const handleTouchEnd = useCallback((e) => {
    setTouchEndX(e.changedTouches[0].clientX);
    handleSwipe();
  }, []);
    
  const handleSwipe = useCallback(() => {
    if (!touchStartX || !touchEndX) return;
    
    const swipeDistance = touchEndX - touchStartX;
    const minSwipeDistance = 10;
    
    // Right swipe and menu is open
    if (swipeDistance > minSwipeDistance && isOpen) {
      setIsOpen(false);
    }
    
    // Reset touch positions
    setTouchStartX(0);
    setTouchEndX(0);
  }, [touchStartX, touchEndX, isOpen]);

  // Initial data loading - only when user info is available
  useEffect(() => {
    if (userInfo && !isLoading) {
      refreshAllData();
    }
  }, [userInfo, isLoading, refreshAllData]);

  return (
    <ThemeProvider>
      <Router>
        <ScrollToTop />
        <Navbar userInfo={userInfo} isOpen={isOpen} setIsOpen={setIsOpen} />
        <div 
          className={`transition-transform duration-300 ${isOpen ? "-translate-x-[40vw]" : "translate-x-0"}`} 
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        > 
          <Routes>  
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <HomePage />
                </PrivateRoute>
              }
            />
            <Route 
              path="/week/:weekNumber" 
              element={
                <PrivateRoute>
                  <WeekPage 
                    games={sortedGames} 
                    moneyLineSelections={moneyLineSelections}
                    propBetSelections={propBetSelections}
                    handleMoneyLineClick={handleMoneyLineClick}
                    handlePropBetClick={handlePropBetClick}
                    gameResults={gameResults}
                    onRefresh={refreshAllData}
                    isRefreshing={isRefreshing}
                  />
                </PrivateRoute>
              } 
            />
            <Route
              path="/login"
              element={
                userInfo ? <Navigate to="/" replace /> : <LoginPage userInfo={userInfo} />
              }
            />
            <Route
              path="/signup"
              element={
                userInfo ? <Navigate to="/" replace /> : <SignUpPage userInfo={userInfo} />
              }
            />
            <Route
              path="/standings"
              element={
                <PrivateRoute>
                  <Standings />
                </PrivateRoute>
              }
            />
            <Route
              path="/weeks"
              element={
                <PrivateRoute>
                  <WeekSelector 
                    games={sortedGames}
                    gameResults={gameResults}
                    moneyLineSelections={moneyLineSelections}
                    propBetSelections={propBetSelections}
                  />
                </PrivateRoute>
              }
            />
          </Routes>
        </div>
      </Router>
    </ThemeProvider>
  );
}