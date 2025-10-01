/*
 * Main App Component - PERFORMANCE OPTIMIZED + ERROR BOUNDARIES
 * Uses useMemo and useCallback to prevent unnecessary re-renders
 * Memoizes expensive operations like sorting and date calculations
 * FIXED: Prevents recreating objects/functions on every render
 * ADDED: Error boundaries around all routes for crash protection
 * ENHANCED: Added minimal draft system for picks
 * CLEANED: Removed floating button logic - now handled by GamePage via Portal
 * TOAST: Clean react-hot-toast implementation - styles moved to CSS
 * 🆕 FULL NAVIGATION PROTECTION: NavigationManager prevents navigation with unsaved picks
 * FIXED: iOS double tap issue by removing global touch handlers
 */

import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
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
import PasswordResetPage from './pages/PasswordResetPage';
import PasswordResetConfirmPage from './pages/PasswordResetConfirmPage';
import PeekPage from './pages/PeekPage';
import PeekSelector from './pages/PeekSelector';
import SettingsPage from './pages/SettingsPage';
import PrivateRoute from './components/common/PrivateRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import NavigationManager from './components/navigation/NavigationManager';
import { useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { getCookie } from './utils/cookies';

// Import the dedicated ScrollToTop component instead of inline version
import ScrollToTop from './components/common/ScrollToTop';

export default function App() {
  const { userInfo, isLoading } = useAuth();
  const [games, setGames] = useState([]);
  const [moneyLineSelections, setMoneyLineSelections] = useState({});
  const [propBetSelections, setPropBetSelections] = useState({});
  const [gameResults, setGameResults] = useState({});
  const [isOpen, setIsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFullPageLoading, setShowFullPageLoading] = useState(false);

  // Draft system
  const [draftPicks, setDraftPicks] = useState({});
  const [draftPropBets, setDraftPropBets] = useState({});
  const [originalSubmittedPicks, setOriginalSubmittedPicks] = useState({});
  const [originalSubmittedPropBets, setOriginalSubmittedPropBets] = useState({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const isAndroid = /android/i.test(navigator.userAgent);

    if (isAndroid) {
      document.body.classList.add('is-android');
      document.body.classList.remove('is-ios');
    } else if (isIOS) {
      document.body.classList.add('is-ios');
      document.body.classList.remove('is-android');

      // iOS 26 Safari bottom address bar fix
      // Prevent fixed elements from shifting when address bar moves
      const iOS26Fix = () => {
        // Use visualViewport API to handle iOS 26's bottom toolbar
        if (window.visualViewport) {
          const viewport = window.visualViewport;

          const handleViewportChange = () => {
            // Calculate offset caused by address bar
            const offsetTop = viewport.offsetTop;
            const offsetBottom = window.innerHeight - (viewport.height + offsetTop);

            // Update CSS custom property for dynamic adjustments
            document.documentElement.style.setProperty('--viewport-offset-top', `${offsetTop}px`);
            document.documentElement.style.setProperty('--viewport-offset-bottom', `${offsetBottom}px`);
          };

          viewport.addEventListener('resize', handleViewportChange);
          viewport.addEventListener('scroll', handleViewportChange);
          handleViewportChange(); // Initial call

          return () => {
            viewport.removeEventListener('resize', handleViewportChange);
            viewport.removeEventListener('scroll', handleViewportChange);
          };
        }
      };

      return iOS26Fix();
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

  // ======== FETCHERS ========

  const fetchGameData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/games/api/games/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
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
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
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
      // 🔁 Swap to analytics feed; map to legacy shape expected by GamePage
      const res = await fetch(`${API_BASE}/predictions/api/game-results/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      });
      if (!res.ok) throw new Error('Failed to fetch game results');

      const data = await res.json();
      const payload = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      const resultsMap = {};

      for (const r of payload) {
        const winner = r?.winner ?? r?.winning_team ?? null;

        // Prefer top-level prop_result; else if exactly one prop exists, use its correct_answer
        const prop_result =
          (r && Object.prototype.hasOwnProperty.call(r, 'prop_result'))
            ? r.prop_result
            : (Array.isArray(r?.prop_bet_results) && r.prop_bet_results.length === 1
                ? r.prop_bet_results[0]?.correct_answer
                : null);

        // Legacy map keyed by game_id
        if (r?.game_id != null) {
          resultsMap[r.game_id] = {
            winner,
            prop_result,
            winning_team: r?.winning_team ?? winner,
            prop_bet_results: Array.isArray(r?.prop_bet_results) ? r.prop_bet_results : undefined,
          };
        }
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

  // Expose refreshAllData globally for navbar sync button
  useEffect(() => {
    window.refreshAllData = async (showLoading = false) => {
      if (showLoading) {
        setShowFullPageLoading(true);
      }
      await refreshAllData();
      if (showLoading) {
        // Keep loading screen for a moment to avoid flash
        setTimeout(() => {
          setShowFullPageLoading(false);
        }, 300);
      }
    };
    window.hasUnsavedChanges = () => hasUnsavedChanges;
    return () => {
      delete window.refreshAllData;
      delete window.hasUnsavedChanges;
    };
  }, [refreshAllData, hasUnsavedChanges]);

  // ======== SUBMIT ========

  const submitPicks = useCallback(async () => {
    if (draftCount === 0) return { success: false, error: "No changes to submit" };
    try {
      for (const [gameId, team] of Object.entries(actualChanges.changedPicks)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ game_id: parseInt(gameId, 10), predicted_winner: team }),
          credentials: 'include',
        });
        if (!response.ok) throw new Error(`Failed to submit pick for game ${gameId}`);
      }
      for (const [propBetId, answer] of Object.entries(actualChanges.changedPropBets)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ prop_bet_id: parseInt(propBetId, 10), answer }),
          credentials: 'include',
        });
        if (!response.ok) throw new Error(`Failed to submit prop bet ${propBetId}`);
      }

      const newOriginalPicks = { ...originalSubmittedPicks, ...actualChanges.changedPicks };
      const newOriginalPropBets = { ...originalSubmittedPropBets, ...actualChanges.changedPropBets };
      setOriginalSubmittedPicks(newOriginalPicks);
      setOriginalSubmittedPropBets(newOriginalPropBets);

      setDraftPicks({});
      setDraftPropBets({});
      setHasUnsavedChanges(false);
      return { success: true };
    } catch (err) {
      console.error("Failed to submit picks:", err);
      return { success: false, error: err.message };
    }
  }, [draftCount, actualChanges, API_BASE, originalSubmittedPicks, originalSubmittedPropBets]);

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

  // Disable browser scroll restoration to prevent interference with our ScrollToTop
  useEffect(() => {
    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }
  }, []);

  // Full page loading screen component
  const FullPageLoading = () => (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100dvh',
      backgroundColor: '#1f1f1f',
      color: 'white',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 99999
    }}>
      <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-500 mb-6"></div>
      <div className="text-2xl font-light text-white tracking-wide mb-2">Hang tight</div>
      <div className="text-sm font-medium text-purple-300 tracking-widest uppercase opacity-75">Loading your experience</div>
    </div>
  );

  // Show loading screen on initial load
  if (isLoading) {
    return <FullPageLoading />;
  }

  return (
    <ThemeProvider>
      <Router>
        {/* Show full page loading screen when syncing */}
        {showFullPageLoading && <FullPageLoading />}

        <NavigationManager hasUnsavedChanges={hasUnsavedChanges} draftCount={draftCount} onClearDrafts={clearDrafts} />
        <ScrollToTop />
        <Navbar userInfo={userInfo} isOpen={isOpen} setIsOpen={setIsOpen} />
        <div className={isOpen ? "transition-transform duration-300 -translate-x-[40vw]" : ""}>
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
              path="/password-reset"
              element={
                <ErrorBoundary level="page" customMessage="Password reset page failed to load">
                  {userInfo ? <Navigate to="/" replace /> : <PasswordResetPage />}
                </ErrorBoundary>
              }
            />
            <Route
              path="/password-reset-confirm/:uidb64/:token"
              element={
                <ErrorBoundary level="page" customMessage="Password reset confirm page failed to load">
                  {userInfo ? <Navigate to="/" replace /> : <PasswordResetConfirmPage />}
                </ErrorBoundary>
              }
            />
            <Route
              path="/standings"
              element={
                <ErrorBoundary level="page" customMessage="Standings page failed to load">
                  <PrivateRoute>
                    <Standings isAuthLoading={isLoading} />
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
                      isAuthLoading={isLoading}
                    />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/peek"
              element={
                <ErrorBoundary level="page" customMessage="Peek selector failed to load">
                  <PrivateRoute>
                    <PeekSelector />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/peek/:weekNumber"
              element={
                <ErrorBoundary level="page" customMessage="Peek page failed to load">
                  <PrivateRoute>
                    <PeekPage />
                  </PrivateRoute>
                </ErrorBoundary>
              }
            />
            <Route
              path="/settings"
              element={
                <PrivateRoute>
                  <SettingsPage />
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
