/*
ResultBanner.jsx
Enhanced progress indicator for WeekPage showing live results tracking
Displays picks made, points scored, and accuracy breakdowns
CSS styles are in App.css
*/

import React from 'react';

export default function ResultBanner({ 
  games, 
  moneyLineSelections, 
  propBetSelections,
  gameResults = {}
}) {
  // Calculate moneyline progress and results
  const calculateMoneyLineResults = () => {
    const totalMoneyLineGames = games.length;
    const madeMoneyLineSelections = games.filter(game => 
      moneyLineSelections[game.id]
    ).length;
    
    // Games with results (winner field populated)
    const gamesWithResults = games.filter(game => 
      gameResults[game.id]?.winner
    );
    
    // Correct moneyline picks
    const correctMoneyLinePicks = gamesWithResults.filter(game => {
      const userPick = moneyLineSelections[game.id];
      const actualWinner = gameResults[game.id]?.winner;
      return userPick && actualWinner && userPick === actualWinner;
    }).length;
    
    return { 
      made: madeMoneyLineSelections, 
      total: totalMoneyLineGames,
      correct: correctMoneyLinePicks,
      withResults: gamesWithResults.length,
      points: correctMoneyLinePicks * 1
    };
  };

  // Calculate prop bet progress and results
  const calculatePropBetResults = () => {
    const gamesWithProps = games.filter(game => 
      game.prop_bets && game.prop_bets.length > 0
    );
    const totalPropBets = gamesWithProps.length;
    const madePropBetSelections = gamesWithProps.filter(game => 
      propBetSelections[game.prop_bets[0]?.id]
    ).length;
    
    // Prop bets with results
    const propBetsWithResults = gamesWithProps.filter(game =>
      gameResults[game.id]?.prop_result !== undefined
    );
    
    // Correct prop picks
    const correctPropPicks = propBetsWithResults.filter(game => {
      const userPick = propBetSelections[game.prop_bets[0]?.id];
      const actualResult = gameResults[game.id]?.prop_result;
      return userPick && actualResult !== undefined && userPick === actualResult;
    }).length;
    
    return { 
      made: madePropBetSelections, 
      total: totalPropBets,
      correct: correctPropPicks,
      withResults: propBetsWithResults.length,
      points: correctPropPicks * 2
    };
  };

  // Calculate overall progress
  const calculateOverallProgress = () => {
    const moneyLineResults = calculateMoneyLineResults();
    const propBetResults = calculatePropBetResults();
    
    const totalPossiblePicks = moneyLineResults.total + propBetResults.total;
    const totalMadePicks = moneyLineResults.made + propBetResults.made;
    const totalGamesWithResults = moneyLineResults.withResults + propBetResults.withResults;
    const totalEarnedPoints = moneyLineResults.points + propBetResults.points;
    
    return { 
      made: totalMadePicks, 
      total: totalPossiblePicks,
      gamesFinished: totalGamesWithResults,
      points: totalEarnedPoints
    };
  };

  const moneyLineResults = calculateMoneyLineResults();
  const propBetResults = calculatePropBetResults();
  const overallProgress = calculateOverallProgress();

  // Calculate percentages (rounded to nearest whole number)
  const moneyLinePercentage = moneyLineResults.withResults > 0 
    ? Math.round((moneyLineResults.correct / moneyLineResults.withResults) * 100)
    : 0;
    
  const propBetPercentage = propBetResults.withResults > 0 
    ? Math.round((propBetResults.correct / propBetResults.withResults) * 100)
    : 0;

  // Don't render if no games available
  if (games.length === 0) {
    return null;
  }

  return (
    <div className="result-banner">
      {/* Top Stats Row */}
      <div className="result-stats-row">
        <div className="stat-group">
          <span className="stat-label">Total Picks</span>
          <span className="stat-value">{overallProgress.made}/{overallProgress.total}</span>
        </div>
        <div className="stat-group">
          <span className="stat-label">Points Scored</span>
          <span className="stat-value points-value">{overallProgress.points}</span>
        </div>
      </div>

      {/* Results Breakdown */}
      <div className="results-breakdown">
        {/* Money Line Section */}
        <div className="result-section">
          <div className="result-section-header">
            <span>Money Line Correct</span>
            <span className="correct-fraction">
              {moneyLineResults.correct}/{moneyLineResults.withResults}
              {moneyLineResults.withResults > 0 && ` (${moneyLinePercentage}%)`}
            </span>
          </div>
          <div className="result-progress-bar">
            <div 
              className="result-progress-fill moneyline-fill" 
              style={{ width: `${moneyLinePercentage}%` }}
            />
          </div>
        </div>

        {/* Prop Bets Section */}
        <div className="result-section">
          <div className="result-section-header">
            <span>Prop Bets Correct</span>
            <span className="correct-fraction">
              {propBetResults.correct}/{propBetResults.withResults}
              {propBetResults.withResults > 0 && ` (${propBetPercentage}%)`}
            </span>
          </div>
          <div className="result-progress-bar">
            <div 
              className="result-progress-fill propbet-fill" 
              style={{ width: `${propBetPercentage}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}