/*
 * REFACTORED: Clean WeekPage Component
 * Modular design with separated concerns
 * FIXED: Pass navigate function to avoid hook issues in nested components
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import WeekHeader from '../components/WeekHeader/WeekHeader.jsx';
import GameCard from '../components/GameCard/GameCard.jsx';
import ProgressIndicator from '../components/ProgressIndicator.jsx';
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
      {/* Header with controls and title */}
      <WeekHeader 
        weekNumber={weekNumber} 
        onRefresh={onRefresh} 
        isRefreshing={isRefreshing}
        onBack={handleBack}
      />

      {/* Scaled content wrapper */}
      <div className="week-page-wrapper">
        {/* Progress indicator */}
        {weekGames.length > 0 && (
          <ProgressIndicator 
            games={weekGames}
            moneyLineSelections={moneyLineSelections}
            propBetSelections={propBetSelections}
            gameResults={gameResults}
          />
        )}

        {/* Games grid */}
        {weekGames.length === 0 ? (
          <p className="text-center" style={{ color: '#9ca3af' }}>
            No games available for this week.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {weekGames.map(game => (
              <GameCard
                key={game.id}
                game={game}
                moneyLineSelections={moneyLineSelections}
                propBetSelections={propBetSelections}
                gameResults={gameResults}
                onMoneyLineClick={handleMoneyLineClick}
                onPropBetClick={handlePropBetClick}
                saveStateManager={saveStateManager}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}