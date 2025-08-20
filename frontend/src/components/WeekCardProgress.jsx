/*
WeekCardProgress.jsx
Compact progress indicator for week selector cards
Reuses ProgressIndicator calculation logic in a card-appropriate design
*/

import React from 'react';

export default function WeekCardProgress({ 
  weekNumber,
  games, 
  moneyLineSelections, 
  propBetSelections 
}) {
  // Filter games for this specific week
  const weekGames = games.filter(game => game.week === weekNumber);
  
  // Reuse the same calculation logic from ProgressIndicator
  const calculateOverallProgress = () => {
    // Calculate moneyline progress
    const totalMoneyLineGames = weekGames.length;
    const madeMoneyLineSelections = weekGames.filter(game => 
      moneyLineSelections[game.id]
    ).length;
    
    // Calculate prop bet progress  
    const gamesWithProps = weekGames.filter(game => 
      game.prop_bets && game.prop_bets.length > 0
    );
    const totalPropBets = gamesWithProps.length;
    const madePropBetSelections = gamesWithProps.filter(game => 
      propBetSelections[game.prop_bets[0]?.id]
    ).length;
    
    // Combine totals
    const totalPossiblePicks = totalMoneyLineGames + totalPropBets;
    const totalMadePicks = madeMoneyLineSelections + madePropBetSelections;
    
    return { 
      made: totalMadePicks, 
      total: totalPossiblePicks
    };
  };

  const progress = calculateOverallProgress();
  
  // Calculate percentage for progress bar
  const progressPercentage = progress.total > 0 
    ? (progress.made / progress.total) * 100 
    : 0;

  // Don't render if no games available for this week
  if (weekGames.length === 0) {
    return null;
  }

  return (
    <div className="week-card-progress">
      {/* Progress bar first */}
      <div className="week-progress-bar">
        <div 
          className="week-progress-fill" 
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      
      {/* Picks text below progress bar */}
      <div className="week-progress-text">
        {progress.made}/{progress.total} picks
      </div>
    </div>
  );
}