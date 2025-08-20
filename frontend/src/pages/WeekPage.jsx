/*
 * PROTECTED: WeekPage Component with Error Boundaries - CLEANED
 * Wraps individual GameCards so one broken game doesn't kill the whole week
 * Protects key components like header and ResultBanner
 * ENHANCED: Added warning banner for draft picks + Portal-based floating submit button
 * TOAST: Clean react-hot-toast implementation
 * 🆕 ERROR-RESILIENT: Submit button with loading state and proper error handling
 * 🧹 CLEANED: Removed save state manager - simple draft system
 * 🗑️ REMOVED: ProgressIndicator (now in WeekSelector cards)
 * 🆕 ADDED: ResultBanner with live scoring and results tracking
 * 🔄 UPDATED: Using new single-line WeekHeader component
 */

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import WeekHeader from '../components/WeekHeader.jsx'; // Updated import path
import GameCard from '../components/GameCard/GameCard.jsx';
import ResultBanner from '../components/ResultBanner.jsx';
import ErrorBoundary from '../components/ErrorBoundary.jsx';

export default function WeekPage({
  games,
  moneyLineSelections,
  propBetSelections,
  handleMoneyLineClick,
  handlePropBetClick,
  gameResults = {},
  onRefresh,
  isRefreshing = false,
  draftCount = 0,
  hasUnsavedChanges = false,
  onSubmitPicks
}) {
  const { weekNumber } = useParams();
  const navigate = useNavigate();
  const weekGames = games.filter(game => game.week === parseInt(weekNumber));
  
  // 🆕 SUBMIT STATE: Track submission loading state
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleBack = () => {
    navigate(-1);
  };

  // 🆕 ENHANCED: Error-resilient submit handler with loading state
  const handleSubmitWithToast = async () => {
    if (isSubmitting || draftCount === 0) return; // Prevent double-clicks
    
    setIsSubmitting(true);
    
    try {
      const result = await onSubmitPicks();
      
      if (result.success) {
        toast.success(`Success! ${draftCount} pick${draftCount !== 1 ? 's' : ''} submitted.`, {
          duration: 4000,
        });
        // onSubmitPicks handles clearing drafts on success
      } else {
        // Show error but keep button available for retry
        toast.error(result.error || "Unable to submit your picks. Please try again.", {
          duration: 5000,
        });
      }
    } catch (error) {
      console.error('Submit error:', error);
      toast.error("Something went wrong. Please check your connection and try again.", {
        duration: 5000,
      });
    } finally {
      // Always reset loading state to re-enable button
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Main WeekPage Content */}
      <div className="pt-16 px-4">
        {/* Header with controls and title - Protected */}
        <ErrorBoundary level="component" customMessage="Header controls failed to load">
          <WeekHeader 
            weekNumber={weekNumber} 
            onBack={handleBack}
          />
        </ErrorBoundary>

        {/* 🆕 RESULT BANNER: Live scoring and results tracking */}
        {weekGames.length > 0 && (
          <ErrorBoundary level="component" customMessage="Results banner failed to load">
            <ResultBanner 
              games={weekGames}
              moneyLineSelections={moneyLineSelections}
              propBetSelections={propBetSelections}
              gameResults={gameResults}
            />
          </ErrorBoundary>
        )}

        {/* 🆕 DRAFT WARNING: Show when user has unsaved picks */}
        {hasUnsavedChanges && (
          <div className="draft-warning-banner">
            ⚠️ You have {draftCount} unsaved pick{draftCount !== 1 ? 's' : ''} - Refresh page to reset, or submit to save
          </div>
        )}

        {/* Scaled content wrapper */}
        <div className="week-page-wrapper">
          {/* Games grid - Each game card individually protected */}
          {weekGames.length === 0 ? (
            <p className="text-center" style={{ color: '#9ca3af' }}>
              No games available for this week.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {weekGames.map(game => (
                <ErrorBoundary 
                  key={game.id} 
                  level="game" 
                  customMessage={`Game ${game.away_team} vs ${game.home_team} failed to load`}
                >
                  <GameCard
                    game={game}
                    moneyLineSelections={moneyLineSelections}
                    propBetSelections={propBetSelections}
                    gameResults={gameResults}
                    onMoneyLineClick={handleMoneyLineClick}
                    onPropBetClick={handlePropBetClick}
                  />
                </ErrorBoundary>
              ))}
            </div>
          )}

          {/* Add some bottom padding so floating button doesn't cover content */}
          <div className="week-page-bottom-padding"></div>
        </div>
      </div>

      {/* 🌟 ENHANCED: Error-resilient floating submit button with loading state */}
      {hasUnsavedChanges && createPortal(
        <button 
          className={`floating-submit-button ${isSubmitting ? 'submitting' : ''}`}
          onClick={handleSubmitWithToast}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span className="submit-spinner"></span>
              {" "}Submitting...
            </>
          ) : (
            `Submit (${draftCount})`
          )}
        </button>,
        document.body  // "Teleport" the button to document.body
      )}
    </>
  );
}