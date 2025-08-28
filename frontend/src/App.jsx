import { BrowserRouter as Router, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import './App.css';
import Navbar from './components/common/Navbar';
import HomePage from './pages/HomePage';
import GamePage from './pages/GamePage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import Standings from './pages/Standings';
import WeekSelector from "./pages/WeekSelector";
import PrivateRoute from './components/common/PrivateRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import NavigationManager from './components/navigation/NavigationManager';
import { useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { getCookie } from './utils/cookies';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
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

  // Draft system
  const [draftPicks, setDraftPicks] = useState({});
  const [draftPropBets, setDraftPropBets] = useState({});
  const [originalSubmittedPicks, setOriginalSubmittedPicks] = useState({});
  const [originalSubmittedPropBets, setOriginalSubmittedPropBets] = useState({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL;

  // --- Robust fetch helpers (handle HTML/redirects and fallback URLs) ---
  async function fetchJSONSafe(url, options = {}) {
    const res = await fetch(url, options);
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    if (!ct.includes('application/json')) {
      const text = await res.text();
      throw new Error(`Expected JSON ${res.status} but got ${ct || 'unknown'} from ${url}: ${text.slice(0,120)}`);
    }
    return res.json();
  }

  async function fetchJSONWithFallback(paths, options = {}) {
    let lastErr;
    for (const path of paths) {
      try {
        return await fetchJSONSafe(`${API_BASE}${path}`, options);
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error('All endpoints failed');
  }

  async function postJSONWithFallback(paths, bodyObj) {
    let lastErr;
    for (const path of paths) {
      try {
        const res = await fetch(`${API_BASE}${path}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          credentials: 'include',
          body: JSON.stringify(bodyObj),
        });
        if (!res.ok) throw new Error(`POST ${path} failed with ${res.status}`);
        // some endpoints reply with no body; swallow JSON parsing errors
        try { return await res.json(); } catch { return { ok: true }; }
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error('All POST endpoints failed');
  }

  useEffect(() => {
    if (/android/i.test(navigator.userAgent)) {
      document.body.classList.add('is-android');
      document.body.classList.remove('is-ios');
    } else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      document.body.classList.add('is-ios');
      document.body.classList.remove('is-android');
    }
  }, []);

  // Clear drafts for NavigationManager
  const clearDrafts = useCallback(() => {
    setDraftPicks({});
    setDraftPropBets({});
    setHasUnsavedChanges(false);
    setMoneyLineSelections(originalSubmittedPicks);
    setPropBetSelections(originalSubmittedPropBets);
  }, [originalSubmittedPicks, originalSubmittedPropBets]);

  // Warn on page refresh/close
  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (hasUnsavedChanges) {
        event.preventDefault();
        event.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return event.returnValue;
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Compute actual changes for submit
  const actualChanges = useMemo(() => {
    const changedPicks = {};
    const changedPropBets = {};
    Object.entries(draftPicks).forEach(([gameId, team]) => {
      if (originalSubmittedPicks[gameId] !== team) changedPicks[gameId] = team;
    });
    Object.entries(draftPropBets).forEach(([propBetId, answer]) => {
      if (originalSubmittedPropBets[propBetId] !== answer) changedPropBets[propBetId] = answer;
    });
    return { changedPicks, changedPropBets };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

  const draftCount = Object.keys(actualChanges.changedPicks).length + Object.keys(actualChanges.changedPropBets).length;

  // ======== FETCHERS (routes fixed with fallbacks) ========

  const fetchGameData = useCallback(async () => {
    try {
      // primary: games app; fallback: analytics mirror if present
      const data = await fetchJSONWithFallback(
        ['/games/api/games/', '/analytics/api/games/'],
        {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        }
      );
      setGames(Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []);
    } catch (err) {
      console.error('Error fetching games:', err);
      setGames([]);
    }
  }, [API_BASE]);

  const fetchUserPredictions = useCallback(async () => {
    try {
      // prefer your current endpoint; tolerate new name; tolerate map or array shapes
      const data = await fetchJSONWithFallback(
        ['/predictions/api/get-user-predictions/', '/predictions/api/user-predictions/'],
        {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        }
      );

      let moneyLine = {};
      let propBets = {};

      // NEW: support map shape { picks: { [gameId]: team }, props: { [propBetId]: answer } }
      if (data && typeof data.picks === 'object' && !Array.isArray(data.picks)) {
        moneyLine = { ...data.picks };
      } else if (Array.isArray(data?.predictions)) {
        moneyLine = data.predictions.reduce((acc, cur) => {
          const gid = cur.game_id ?? cur.game;
          acc[gid] = cur.predicted_winner ?? cur.pick ?? null;
          return acc;
        }, {});
      }

      if (data && typeof data.props === 'object' && !Array.isArray(data.props)) {
        propBets = { ...data.props };
      } else if (Array.isArray(data?.prop_bets)) {
        propBets = data.prop_bets.reduce((acc, cur) => {
          const pid = cur.prop_bet_id ?? cur.prop_bet ?? cur.id;
          const ans = cur.answer ?? cur.selected_answer ?? cur.choice ?? null;
          acc[pid] = ans;
          return acc;
        }, {});
      }

      setMoneyLineSelections(moneyLine);
      setPropBetSelections(propBets);
      setOriginalSubmittedPicks(moneyLine);
      setOriginalSubmittedPropBets(propBets);
    } catch (err) {
      console.error('Error fetching predictions:', err);
      setMoneyLineSelections({});
      setPropBetSelections({});
      setOriginalSubmittedPicks({});
      setOriginalSubmittedPropBets({});
    }
  }, [API_BASE]);

  const fetchGameResults = useCallback(async () => {
    try {
      // analytics likely owns read endpoints now; fall back to legacy
      const data = await fetchJSONWithFallback(
        ['/analytics/api/game-results/', '/games/api/game-results/', '/predictions/api/game-results/'],
        {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        }
      );

      const payload = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      const resultsMap = {};

      for (const r of payload) {
        const winner = r?.winner ?? r?.winning_team ?? null;
        const prop_result =
          (r && Object.prototype.hasOwnProperty.call(r, 'prop_result'))
            ? r.prop_result
            : (Array.isArray(r?.prop_bet_results) && r.prop_bet_results.length === 1
                ? r.prop_bet_results[0]?.correct_answer
                : null);

        const gid = r.game_id ?? r.id;
        resultsMap[gid] = {
          winner,
          prop_result,
          winning_team: r?.winning_team ?? winner,
          prop_bet_results: Array.isArray(r?.prop_bet_results) ? r.prop_bet_results : undefined,
        };
      }

      setGameResults(resultsMap);
    } catch (err) {
      console.error('Error fetching game results:', err);
      setGameResults({});
    }
  }, [API_BASE]);

  // Combine refresh
  const refreshAllData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchGameData(), fetchUserPredictions(), fetchGameResults()]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchGameData, fetchUserPredictions, fetchGameResults]);

  // ======== SUBMIT ========

  const submitPicks = useCallback(async () => {
    if (draftCount === 0) return { success: false, error: "No changes to submit" };
    try {
      // moneyline picks
      for (const [gameId, team] of Object.entries(actualChanges.changedPicks)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ game_id: parseInt(gameId, 10), predicted_winner: team }),
          credentials: 'include',
        });
        if (!response.ok) throw new Error(`Failed to submit pick for game ${gameId}`);
      }

      // prop picks
      for (const [propBetId, answer] of Object.entries(actualChanges.changedPropBets)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ prop_bet_id: parseInt(propBetId, 10), answer }),
          credentials: 'include',
        });
        if (!response.ok) throw new Error(`Failed to submit prop bet ${propBetId}`);
      }

      // Optimistic update (what you already had)
      const newOriginalPicks = { ...originalSubmittedPicks, ...actualChanges.changedPicks };
      const newOriginalPropBets = { ...originalSubmittedPropBets, ...actualChanges.changedPropBets };
      setOriginalSubmittedPicks(newOriginalPicks);
      setOriginalSubmittedPropBets(newOriginalPropBets);
      setDraftPicks({});
      setDraftPropBets({});
      setHasUnsavedChanges(false);

      // 🔁 NEW: pull from server so UI reflects persisted answers immediately
      await Promise.all([fetchUserPredictions(), fetchGameResults()]);

      return { success: true };
    } catch (err) {
      console.error("Failed to submit picks:", err);
      return { success: false, error: err.message };
    }
  }, [
    draftCount,
    actualChanges,
    API_BASE,
    originalSubmittedPicks,
    originalSubmittedPropBets,
    fetchUserPredictions,
    fetchGameResults
  ]);

  // ======== CLICK HANDLERS ========

  const handleMoneyLineClick = useCallback(async (game, team) => {
    if (game.locked) return;
    setDraftPicks(prev => ({ ...prev, [game.id]: team }));

    const updatedDrafts = { ...draftPicks, [game.id]: team };
    const hasChanges =
      Object.entries(updatedDrafts).some(([gid, draftTeam]) => originalSubmittedPicks[gid] !== draftTeam) ||
      Object.entries(draftPropBets).some(([pid, draftAnswer]) => originalSubmittedPropBets[pid] !== draftAnswer);
    setHasUnsavedChanges(hasChanges);

    setMoneyLineSelections(prev => ({ ...prev, [game.id]: team }));
    return { success: true };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

  const handlePropBetClick = useCallback(async (game, answer) => {
    if (game.locked) return;
    const propBetId = game.prop_bets?.[0]?.id;
    if (!propBetId) return;

    setDraftPropBets(prev => ({ ...prev, [propBetId]: answer }));

    const updatedDraftPropBets = { ...draftPropBets, [propBetId]: answer };
    const hasChanges =
      Object.entries(draftPicks).some(([gid, draftTeam]) => originalSubmittedPicks[gid] !== draftTeam) ||
      Object.entries(updatedDraftPropBets).some(([pid, draftAnswer]) => originalSubmittedPropBets[pid] !== draftAnswer);
    setHasUnsavedChanges(hasChanges);

    setPropBetSelections(prev => ({ ...prev, [propBetId]: answer }));
    return { success: true };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

  // ======== SORT + LOAD ========

  const sortedGames = useMemo(() => {
    if (!Array.isArray(games)) return [];
    const gamesWithDates = games.map(game => ({ ...game, _sortDate: new Date(game.start_time).getTime() }));
    return gamesWithDates.sort((a, b) => a._sortDate - b._sortDate);
  }, [games]);

  useEffect(() => {
    if (userInfo && !isLoading) refreshAllData();
  }, [userInfo, isLoading, refreshAllData]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#1f1f1f', color: 'white' }}>
        Loading...
      </div>
    );
  }

  return (
    <ThemeProvider>
      <Router>
        <NavigationManager hasUnsavedChanges={hasUnsavedChanges} draftCount={draftCount} onClearDrafts={clearDrafts} />
        <ScrollToTop />
        <Navbar userInfo={userInfo} isOpen={isOpen} setIsOpen={setIsOpen} />
        <div className={`transition-transform duration-300 ${isOpen ? "-translate-x-[40vw]" : "translate-x-0"}`}>
          <Routes>
            <Route
              path="/"
              element={
                <ErrorBoundary level="page" customMessage="Home page failed to load">
                  <PrivateRoute>
                    <HomePage />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/week/:weekNumber"
              element={
                <ErrorBoundary level="page" customMessage="Week page failed to load">
                  <PrivateRoute>
                    <GamePage
                      games={sortedGames}
                      moneyLineSelections={moneyLineSelections}
                      propBetSelections={propBetSelections}
                      handleMoneyLineClick={handleMoneyLineClick}
                      handlePropBetClick={handlePropBetClick}
                      gameResults={gameResults}
                      onRefresh={refreshAllData}
                      isRefreshing={isRefreshing}
                      draftCount={draftCount}
                      hasUnsavedChanges={hasUnsavedChanges}
                      onSubmitPicks={submitPicks}
                      originalSubmittedPicks={originalSubmittedPicks}
                      originalSubmittedPropBets={originalSubmittedPropBets}
                      draftPicks={draftPicks}
                      draftPropBets={draftPropBets}
                    />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/login"
              element={
                <ErrorBoundary level="page" customMessage="Login page failed to load">
                  {userInfo ? <Navigate to="/" replace /> : <LoginPage userInfo={userInfo} />}
                </ErrorBoundary>
              }
            />
            <Route
              path="/signup"
              element={
                <ErrorBoundary level="page" customMessage="Sign up page failed to load">
                  {userInfo ? <Navigate to="/" replace /> : <SignUpPage userInfo={userInfo} />}
                </ErrorBoundary>
              }
            />
            <Route
              path="/standings"
              element={
                <ErrorBoundary level="page" customMessage="Standings page failed to load">
                  <PrivateRoute>
                    <Standings />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/weeks"
              element={
                <ErrorBoundary level="page" customMessage="Week selector failed to load">
                  <PrivateRoute>
                    <WeekSelector
                      games={sortedGames}
                      gameResults={gameResults}
                      moneyLineSelections={moneyLineSelections}
                      propBetSelections={propBetSelections}
                      originalSubmittedPicks={originalSubmittedPicks}
                      originalSubmittedPropBets={originalSubmittedPropBets}
                    />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/settings"
              element={
                <PrivateRoute>
                  <div style={{ padding: '80px 20px 20px,', color: 'white', textAlign: 'center' }}>
                    <h1>Coming Soon!</h1>
                  </div>
                </PrivateRoute>
              }
            />
          </Routes>
        </div>

        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            className: 'custom-toast',
            success: { className: 'custom-toast-success' },
            error: { className: 'custom-toast-error' },
          }}
          containerClassName="toast-container"
        />
      </Router>
    </ThemeProvider>
  );
}