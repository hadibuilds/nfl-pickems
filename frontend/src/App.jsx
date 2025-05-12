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
  const [isOpen, setIsOpen] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
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

    if (userInfo && !isLoading) {
      fetchGameData();
      fetchUserPredictions();
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
      if (data.success) setMoneyLineSelections(updated);
    } catch (err) {
      console.error("Failed to save moneyline selection:", err);
    }
  };

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
      if (data.success) setPropBetSelections(updated);
    } catch (err) {
      console.error("Failed to save prop bet selection:", err);
    }
  };

  const sortedGames = Array.isArray(games)
    ? [...games].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    : [];

  return (
    <Router>
      <ScrollToTop />
      <Navbar userInfo={userInfo} onLogout={logout} isOpen={isOpen} setIsOpen={setIsOpen} />
      <div className={`transition-transform duration-300 ${isOpen ? "-translate-x-64" : "translate-x-0"}`}>
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
                <WeekSelector />
              </PrivateRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}