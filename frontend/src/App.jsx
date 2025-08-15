/*
 * Main App Component with Game Results Support and Theme Provider
 * Fetches games, user predictions, and game results for showing pick accuracy
 * Passes all data to WeekPage for displaying checkmarks on correct/incorrect picks
 * Wraps entire app with ThemeProvider for light/dark mode toggle
 */

import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import React, { useState, useEffect } from 'react';
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
  const { userInfo, isLoading, logout } = useAuth();
  const [games, setGames] = useState([]);
  const [moneyLineSelections, setMoneyLineSelections] = useState({});
  const [propBetSelections, setPropBetSelections] = useState({});
  const [gameResults, setGameResults] = useState({});
  const [isOpen, setIsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [touchStartX, setTouchStartX] = useState(0);
const [touchEndX, setTouchEndX] = useState(0);

  const API_BASE = import.meta.env.VITE_API_URL;

  // Extract data fetching into separate functions for reuse
  const fetchGameData = async () => {
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
  };

  const fetchUserPredictions = async () => {
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
  };

  const fetchGameResults = async () => {
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
  };

  // Refresh all data
  const refreshAllData = async () => {
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
  };

  useEffect(() => {
    if (userInfo && !isLoading) {
      refreshAllData();
    }
  }, [userInfo, isLoading]);

  const handleMoneyLineClick = async (game, team) => {
    if (game.locked) return;
    const updated = { ...moneyLineSelections, [game.id]: team };
  
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
        setMoneyLineSelections(updated);
        return data; // Return success data
      } else {
        throw new Error(data.message || 'Save failed');
      }
    } catch (err) {
      console.error("Failed to save moneyline selection:", err);
      throw err; // Re-throw to trigger error state in WeekPage
    }
  };
  
  // Find this function in your App.jsx and replace it:
  const handlePropBetClick = async (game, answer) => {
    if (game.locked) return;
    const propBetId = game.prop_bets?.[0]?.id;
    if (!propBetId) return;
  
    const updated = { ...propBetSelections, [propBetId]: answer };
  
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
        setPropBetSelections(updated);
        return data; // Return success data
      } else {
        throw new Error(data.message || 'Save failed');
      }
    } catch (err) {
      console.error("Failed to save prop bet selection:", err);
      throw err; // Re-throw to trigger error state in WeekPage
    }
  };
  const sortedGames = Array.isArray(games)
    ? [...games].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    : [];
  
  const handleTouchStart = (e) => {
      setTouchStartX(e.targetTouches[0].clientX);
  };
    
  const handleTouchEnd = (e) => {
      setTouchEndX(e.changedTouches[0].clientX);
      handleSwipe();
  };
    
  const handleSwipe = () => {
      if (!touchStartX || !touchEndX) return;
      
      const swipeDistance = touchEndX - touchStartX;
      const minSwipeDistance = 20; // Minimum pixels for a valid swipe
      
      // Right swipe (positive distance) and menu is open
      if (swipeDistance > minSwipeDistance && isOpen) {
        setIsOpen(false);
      }
      
      // Reset touch positions
      setTouchStartX(0);
      setTouchEndX(0);
   };

  return (
    <ThemeProvider>
      <Router>
        <ScrollToTop />
        <Navbar userInfo={userInfo} onLogout={logout} isOpen={isOpen} setIsOpen={setIsOpen} />
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