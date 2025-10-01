/*
 * PROTECTED: GamePage Component with Error Boundaries - CLEANED
 * Wraps individual GameCards so one broken game doesn't kill the whole week
 * Protects key components like header and ResultBanner
 * ENHANCED: Added warning banner for draft picks + Portal-based floating submit button
 * TOAST: Clean react-hot-toast implementation
 * 🆕 ERROR-RESILIENT: Submit button with loading state and proper error handling
 * 🧹 CLEANED: Removed save state manager - simple draft system
 * 🗑️ REMOVED: ProgressIndicator (now in WeekSelector cards)
 * 🆕 ADDED: ResultBanner with live scoring and results tracking
 * 🔄 UPDATED: Using new single-line WeekHeader component
 * 🔒 NAVIGATION PROTECTED: Back button uses navigateWithConfirmation
 * 🎨 DRAFT STYLING: Passes draft state to GameCard for yellow borders
 */

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import WeekHeader from '../components/weeks/WeekHeader.jsx'; 
import GameCard from '../components/game/GameCard.jsx';
import ResultBanner from '../components/weeks/ResultBanner.jsx';
import QuickViewModal from '../components/game/QuickViewModal.jsx';
import ErrorBoundary from '../components/common/ErrorBoundary.jsx';

export default function GamePage({
  games,
  moneyLineSelections,
  propBetSelections,
  handleMoneyLineClick,
  handlePropBetClick,
  gameResults = {},
  draftCount = 0,
  hasUnsavedChanges = false,
  onSubmitPicks,
  originalSubmittedPicks = {},
  originalSubmittedPropBets = {},
  // 🆕 DRAFT PROPS: For yellow border styling
  draftPicks = {},
  draftPropBets = {}
}) {
  const { weekNumber } = useParams();
  const weekGames = games.filter(game => game.week === parseInt(weekNumber));
  
  // 🆕 SUBMIT STATE: Track submission loading state
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // 🆕 QUICK VIEW STATE: Track modal visibility
  const [showQuickView, setShowQuickView] = useState(false);

  // 🔒 PROTECTED BACK NAVIGATION: Uses navigateWithConfirmation
  const handleBack = () => {
    if (window.navigateWithConfirmation) {
      // Use protected navigation if NavigationManager is active
      window.navigateWithConfirmation('/weeks');
    } else {
      // Fallback for when NavigationManager is not active
      window.history.back();
    }
  };

  // 🆕 QUICK VIEW: Handle modal open/close
  const handleQuickView = () => {
    setShowQuickView(true);
  };

  const handleCloseQuickView = () => {
    setShowQuickView(false);
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
      {/* Main GamePage Content */}
      <div
        className="px-4 game-page-content"
        style={{
          paddingTop: 'calc(64px + env(safe-area-inset-top, 0px))',
        }}
      >
        {/* Header with controls and title - Protected */}
        <ErrorBoundary level="component" customMessage="Header controls failed to load">
          <WeekHeader 
            weekNumber={weekNumber} 
            onBack={handleBack}
            onQuickView={handleQuickView}
          />
        </ErrorBoundary>

        {/* 🆕 RESULT BANNER: Live scoring and results tracking */}
        {weekGames.length > 0 && (
          <ErrorBoundary level="component" customMessage="Results banner failed to load">
            <div className="max-w-4xl mx-auto">
              <ResultBanner 
                games={weekGames}
                originalSubmittedPicks={originalSubmittedPicks}
                originalSubmittedPropBets={originalSubmittedPropBets}
                gameResults={gameResults}
              />
            </div>
          </ErrorBoundary>
        )}

        {/* Games grid - Each game card individually protected */}
        {weekGames.length === 0 ? (
          <p className="text-center" style={{ color: '#9ca3af' }}>
            No games available for this week.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto justify-items-center">
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
                  originalSubmittedPicks={originalSubmittedPicks}
                  originalSubmittedPropBets={originalSubmittedPropBets}
                  draftPicks={draftPicks}
                  draftPropBets={draftPropBets}
                />
              </ErrorBoundary>
              ))}
          </div>
        )}

        {/* Add some bottom padding so floating button doesn't cover content */}
        <div className="week-page-bottom-padding"></div>
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

      {/* 🆕 QUICK VIEW MODAL */}
      <QuickViewModal 
        isOpen={showQuickView}
        onClose={handleCloseQuickView}
        weekNumber={weekNumber}
        games={weekGames}
        moneyLineSelections={moneyLineSelections}
        propBetSelections={propBetSelections}
      />
    </>
  );

}
