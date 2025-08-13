/*
 * Enhanced ProgressIndicator Component
 * Displays pick completion progress and points earned
 * Moneyline picks = 1 point, Prop bets = 2 points
 * Shows separate tracking for games vs props and total points earned
 */

import React from 'react';

export default function ProgressIndicator({ 
  games, 
  moneyLineSelections, 
  propBetSelections,
  gameResults = {} // Object with game results for point calculation
}) {
  // Calculate moneyline progress and points
  const calculateMoneyLineProgress = () => {
    const totalMoneyLineGames = games.length;
    const madeMoneyLineSelections = games.filter(game => 
      moneyLineSelections[game.id]
    ).length;
    
    // Calculate points earned from correct moneyline picks
    const correctMoneyLinePicks = games.filter(game => {
      const userPick = moneyLineSelections[game.id];
      const actualWinner = gameResults[game.id]?.winner;
      return userPick && actualWinner && userPick === actualWinner;
    }).length;
    
    return { 
      made: madeMoneyLineSelections, 
      total: totalMoneyLineGames,
      points: correctMoneyLinePicks * 1
    };
  };

  // Calculate prop bet progress and points
  const calculatePropBetProgress = () => {
    const gamesWithProps = games.filter(game => 
      game.prop_bets && game.prop_bets.length > 0
    );
    const totalPropBets = gamesWithProps.length;
    const madePropBetSelections = gamesWithProps.filter(game => 
      propBetSelections[game.prop_bets[0]?.id]
    ).length;
    
    // Calculate points earned from correct prop bets
    const correctPropPicks = gamesWithProps.filter(game => {
      const userPick = propBetSelections[game.prop_bets[0]?.id];
      const actualResult = gameResults[game.id]?.prop_result;
      return userPick && actualResult && userPick === actualResult;
    }).length;
    
    return { 
      made: madePropBetSelections, 
      total: totalPropBets,
      points: correctPropPicks * 2
    };
  };

  // Calculate overall progress and points
  const calculateOverallProgress = () => {
    const moneyLineProgress = calculateMoneyLineProgress();
    const propBetProgress = calculatePropBetProgress();
    
    const totalPossiblePicks = moneyLineProgress.total + propBetProgress.total;
    const totalMadePicks = moneyLineProgress.made + propBetProgress.made;
    const totalPossiblePoints = (moneyLineProgress.total * 1) + (propBetProgress.total * 2);
    const totalEarnedPoints = moneyLineProgress.points + propBetProgress.points;
    
    return { 
      made: totalMadePicks, 
      total: totalPossiblePicks,
      points: totalEarnedPoints,
      maxPoints: totalPossiblePoints
    };
  };

  const overallProgress = calculateOverallProgress();
  const moneyLineProgress = calculateMoneyLineProgress();
  const propBetProgress = calculatePropBetProgress();
  
  // Calculate percentage for progress bar (based on picks made)
  const progressPercentage = overallProgress.total > 0 
    ? (overallProgress.made / overallProgress.total) * 100 
    : 0;

  // Don't render if no games available
  if (games.length === 0) {
    return null;
  }

  // Check if any games have results (to show points)
  const hasResults = overallProgress.points > 0;

  return (
    <div className="progress-indicator">
      {/* Picks made - above progress bar */}
      <div className="progress-text" style={{ fontSize: '1.3rem' }}>
        <span>Picks made: {overallProgress.made}/{overallProgress.total}</span>
      </div>
      
      {/* Progress bar */}
      <div className="progress-bar" style={{ width: '300px' }}>
        <div 
          className="progress-fill" 
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      
      {/* Points - below progress bar */}
      {hasResults && (
        <div style={{ 
          fontSize: '1.2rem', 
          color: '#10B981', 
          fontWeight: '600',
          marginTop: '8px',
          textAlign: 'center'
        }}>
          Points: {overallProgress.points}/{overallProgress.maxPoints}
        </div>
      )}
    </div>
  );
}