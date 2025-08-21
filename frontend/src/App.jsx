/*
 * Main App Component - PERFORMANCE OPTIMIZED + ERROR BOUNDARIES
 * Uses useMemo and useCallback to prevent unnecessary re-renders
 * Memoizes expensive operations like sorting and date calculations
 * FIXED: Prevents recreating objects/functions on every render
 * ADDED: Error boundaries around all routes for crash protection
 * ENHANCED: Added minimal draft system for picks
 * CLEANED: Removed floating button logic - now handled by WeekPage via Portal
 * TOAST: Clean react-hot-toast implementation - styles moved to CSS
 * 🆕 BASIC NAVIGATION PROTECTION: Browser refresh/close warning only
 */

import { BrowserRouter as Router, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import './App.css';
import Navbar from './components/common/Navbar';
import HomePage from './pages/HomePage';
import WeekPage from './pages/WeekPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import Standings from './pages/Standings';
import WeekSelector from "./pages/WeekSelector"; 
import PrivateRoute from './components/common/PrivateRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import { useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { getCookie } from './utils/cookies';

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

  // 🆕 DRAFT SYSTEM: Local draft state + original submitted state
  const [draftPicks, setDraftPicks] = useState({});
  const [draftPropBets, setDraftPropBets] = useState({});
  const [originalSubmittedPicks, setOriginalSubmittedPicks] = useState({});
  const [originalSubmittedPropBets, setOriginalSubmittedPropBets] = useState({});
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    if (/android/i.test(navigator.userAgent)) {
      document.body.classList.add('is-android');
      document.body.classList.remove('is-ios');
    } else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      document.body.classList.add('is-ios');
      document.body.classList.remove('is-android');
    }
  }, []);

  // 🆕 BASIC BROWSER PROTECTION: Warn on page refresh/close
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

  // Calculate ACTUAL changes (not just drafts) for UI
  const actualChanges = useMemo(() => {
    const changedPicks = {};
    const changedPropBets = {};

    // Check moneyline picks - only count if different from original
    Object.entries(draftPicks).forEach(([gameId, team]) => {
      if (originalSubmittedPicks[gameId] !== team) {
        changedPicks[gameId] = team;
      }
    });

    // Check prop bet picks - only count if different from original  
    Object.entries(draftPropBets).forEach(([propBetId, answer]) => {
      if (originalSubmittedPropBets[propBetId] !== answer) {
        changedPropBets[propBetId] = answer;
      }
    });

    return { changedPicks, changedPropBets };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

  const draftCount = Object.keys(actualChanges.changedPicks).length + Object.keys(actualChanges.changedPropBets).length;

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

      // Store current predictions as both UI state and original submitted state
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

  // 🆕 ENHANCED: Submit only actual changes to database
  const submitPicks = useCallback(async () => {
    if (draftCount === 0) return { success: false, error: "No changes to submit" };

    try {
      console.log('🚀 Submitting actual changes:', actualChanges);

      // Submit only changed moneyline picks
      for (const [gameId, team] of Object.entries(actualChanges.changedPicks)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: JSON.stringify({ game_id: parseInt(gameId), predicted_winner: team }),
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`Failed to submit pick for game ${gameId}`);
        }
      }

      // Submit only changed prop bet picks
      for (const [propBetId, answer] of Object.entries(actualChanges.changedPropBets)) {
        const response = await fetch(`${API_BASE}/predictions/api/save-selection/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: JSON.stringify({ prop_bet_id: parseInt(propBetId), answer }),
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`Failed to submit prop bet ${propBetId}`);
        }
      }

      // Update original submitted state to current state
      const newOriginalPicks = { ...originalSubmittedPicks, ...actualChanges.changedPicks };
      const newOriginalPropBets = { ...originalSubmittedPropBets, ...actualChanges.changedPropBets };
      
      setOriginalSubmittedPicks(newOriginalPicks);
      setOriginalSubmittedPropBets(newOriginalPropBets);

      // Clear drafts and update state
      setDraftPicks({});
      setDraftPropBets({});
      setHasUnsavedChanges(false);
      
      console.log('✅ All changes submitted successfully!');
      return { success: true };

    } catch (err) {
      console.error("Failed to submit picks:", err);
      return { success: false, error: err.message };
    }
  }, [draftCount, actualChanges, API_BASE, originalSubmittedPicks, originalSubmittedPropBets]);

  // 🆕 ENHANCED: Check if pick is actually different from original before setting unsaved changes
  const handleMoneyLineClick = useCallback(async (game, team) => {
    if (game.locked) return;

    console.log('💾 Storing draft pick:', { gameId: game.id, team });

    // Store as draft locally
    setDraftPicks(prev => ({ ...prev, [game.id]: team }));
    
    // Check if we have any actual changes from original submitted picks
    const updatedDrafts = { ...draftPicks, [game.id]: team };
    const hasChanges = Object.entries(updatedDrafts).some(([gameId, draftTeam]) => 
      originalSubmittedPicks[gameId] !== draftTeam
    ) || Object.entries(draftPropBets).some(([propBetId, draftAnswer]) => 
      originalSubmittedPropBets[propBetId] !== draftAnswer
    );
    
    setHasUnsavedChanges(hasChanges);

    // Update UI immediately (same visual experience as before)
    setMoneyLineSelections(prev => ({ ...prev, [game.id]: team }));

    return { success: true };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

  // 🆕 ENHANCED: Check if prop bet is actually different from original before setting unsaved changes
  const handlePropBetClick = useCallback(async (game, answer) => {
    if (game.locked) return;
    const propBetId = game.prop_bets?.[0]?.id;
    if (!propBetId) return;

    console.log('💾 Storing draft prop bet:', { propBetId, answer });

    // Store as draft locally
    setDraftPropBets(prev => ({ ...prev, [propBetId]: answer }));
    
    // Check if we have any actual changes from original submitted picks
    const updatedDraftPropBets = { ...draftPropBets, [propBetId]: answer };
    const hasChanges = Object.entries(draftPicks).some(([gameId, draftTeam]) => 
      originalSubmittedPicks[gameId] !== draftTeam
    ) || Object.entries(updatedDraftPropBets).some(([propId, draftAnswer]) => 
      originalSubmittedPropBets[propId] !== draftAnswer
    );
    
    setHasUnsavedChanges(hasChanges);

    // Update UI immediately (same visual experience as before)
    setPropBetSelections(prev => ({ ...prev, [propBetId]: answer }));

    return { success: true };
  }, [draftPicks, draftPropBets, originalSubmittedPicks, originalSubmittedPropBets]);

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
                    <WeekPage 
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
            <Route path="/settings" element={
              <PrivateRoute>
                <div style={{padding: '80px 20px 20px', color: 'white', textAlign: 'center'}}>
                  <h1>Coming Soon!</h1>
                </div>
              </PrivateRoute>
            } />
          </Routes>
        </div>
        
        {/* Simple Toaster with minimal config - styles moved to CSS */}
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            className: 'custom-toast',
            success: {
              className: 'custom-toast-success',
            },
            error: {
              className: 'custom-toast-error',
            },
          }}
          containerClassName="toast-container"
        />
      </Router>
    </ThemeProvider>
  );
}