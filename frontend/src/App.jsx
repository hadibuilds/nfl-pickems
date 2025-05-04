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

const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

export default function App() {
  const { userInfo, isLoading, logout } = useAuth();
  const [games, setGames] = useState([]);
  const [moneyLineSelections, setMoneyLineSelections] = useState({});
  const [propBetSelections, setPropBetSelections] = useState({});
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!userInfo || isLoading) return;

    fetch('http://localhost:8000/games/api/games/', {
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
      .then(response => {
        if (!response.ok) throw new Error('Failed to fetch games');
        return response.json();
      })
      .then(data => setGames(data))
      .catch(error => {
        console.error('Error fetching games:', error);
        setGames([]);
      });

    fetch('http://localhost:8000/predictions/api/get-user-predictions/', {
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
      .then(response => {
        if (!response.ok) throw new Error('Failed to fetch predictions');
        return response.json();
      })
      .then(data => {
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
      })
      .catch(error => {
        console.error('Error fetching predictions:', error);
        setMoneyLineSelections({});
        setPropBetSelections({});
      });
  }, [userInfo, isLoading]);

  const handleMoneyLineClick = (game, team) => {
    if (game.locked) return;

    const updated = { ...moneyLineSelections, [game.id]: team };
    fetch('http://localhost:8000/predictions/api/save-selection/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ game_id: game.id, predicted_winner: team }),
      credentials: 'include',
    })
      .then(res => res.json())
      .then(data => data.success && setMoneyLineSelections(updated))
      .catch(console.error);
  };

  const handlePropBetClick = (game, answer) => {
    if (game.locked) return;

    const propBetId = game.prop_bets?.[0]?.id;
    if (!propBetId) return;

    const updated = { ...propBetSelections, [propBetId]: answer };
    fetch('http://localhost:8000/predictions/api/save-selection/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ prop_bet_id: propBetId, answer }),
      credentials: 'include',
    })
      .then(res => res.json())
      .then(data => data.success && setPropBetSelections(updated))
      .catch(console.error);
  };

  const sortedGames = Array.isArray(games)
    ? [...games].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    : [];

  return (
    <Router>
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
