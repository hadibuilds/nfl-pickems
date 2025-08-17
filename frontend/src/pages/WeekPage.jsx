/*
 * PROTECTED: WeekPage Component with Error Boundaries
 * Wraps individual GameCards so one broken game doesn't kill the whole week
 * Protects key components like header and progress indicator
 * FIXED: Pass navigate function to avoid hook issues in nested components
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import WeekHeader from '../components/WeekHeader/WeekHeader.jsx';
import GameCard from '../components/GameCard/GameCard.jsx';
import ProgressIndicator from '../components/ProgressIndicator.jsx';
import ErrorBoundary from '../components/ErrorBoundary.jsx';
import { useSaveStateManager } from '../utils/saveStateManager.js';

export default function WeekPage({
  games,
  moneyLineSelections,
  propBetSelections,
  handleMoneyLineClick,
  handlePropBetClick,
  gameResults = {},
  onRefresh,
  isRefreshing = false
}) {
  const { weekNumber } = useParams();
  const navigate = useNavigate();
  const weekGames = games.filter(game => game.week === parseInt(weekNumber));
  
  // FIXED: Proper save state management with cleanup
  const saveStateManager = useSaveStateManager();

  const handleBack = () => {
    navigate(-1);
  };

  return (
    <div className="pt-16 px-4">
      {/* Header with controls and title - Protected */}
      <ErrorBoundary level="component" customMessage="Header controls failed to load">
        <WeekHeader 
          weekNumber={weekNumber} 
          onRefresh={onRefresh} 
          isRefreshing={isRefreshing}
          onBack={handleBack}
        />
      </ErrorBoundary>

      {/* Scaled content wrapper */}
      <div className="week-page-wrapper">
        {/* Progress indicator - Protected */}
        {weekGames.length > 0 && (
          <ErrorBoundary level="component" customMessage="Progress indicator failed to load">
            <ProgressIndicator 
              games={weekGames}
              moneyLineSelections={moneyLineSelections}
              propBetSelections={propBetSelections}
              gameResults={gameResults}
            />
          </ErrorBoundary>
        )}

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
                  saveStateManager={saveStateManager}
                />
              </ErrorBoundary>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}