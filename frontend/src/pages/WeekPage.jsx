/*
 * Cleaned WeekPage Component - PURE CSS ONLY
 * Removed ALL Tailwind classes to fix mobile/desktop inconsistencies
 * Uses only custom CSS classes for consistent styling
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ProgressIndicator from '../components/ProgressIndicator';

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

  // Use real results from backend
  const activeGameResults = gameResults;
  
  console.log('🎮 WeekPage gameResults prop:', gameResults);
  console.log('🎯 Active game results:', activeGameResults);

  // Helper function to format date and time
  const formatGameDateTime = (startTime) => {
    const gameDate = new Date(startTime);
    const dayAndDate = gameDate.toLocaleDateString('en-US', {
      weekday: 'short',
      month: '2-digit',
      day: '2-digit',
    });
    const formattedTime = gameDate.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
    
    return { dayAndDate, formattedTime };
  };

  // Helper function to get section result indicator
  const getSectionResultIndicator = (game, isMoneyLineSection, gameIndex) => {
    if (!activeGameResults[game.id]) return null;
    
    let userSelection, actualResult;
    
    if (isMoneyLineSection) {
      userSelection = moneyLineSelections[game.id];
      actualResult = activeGameResults[game.id].winner;
    } else {
      if (!game.prop_bets || game.prop_bets.length === 0) return null;
      userSelection = propBetSelections[game.prop_bets[0].id];
      actualResult = activeGameResults[game.id].prop_result;
    }
    
    if (!userSelection || !actualResult) return null;
    
    const isCorrect = userSelection === actualResult;
    
    return (
      <div 
        style={{
          position: 'absolute',
          top: isMoneyLineSection ? '6px' : 'auto',
          bottom: isMoneyLineSection ? 'auto' : '6px', 
          right: '8px',
          fontSize: '18px',
          fontWeight: 'bold',
          zIndex: 1000,
          pointerEvents: 'none',
          color: isCorrect ? '#10B981' : '#EF4444',
          lineHeight: '1',
          width: '0px',
          height: '0px',
          overflow: 'visible',
          margin: '0',
          padding: '0',
          border: 'none',
          outline: 'none'
        }}
      >
        <span style={{
          position: 'absolute',
          right: '0',
          top: '0',
          display: 'block',
          width: '18px',
          height: '18px',
          textAlign: 'center'
        }}>
          {isCorrect ? '✓' : '✗'}
        </span>
      </div>
    );
  };

  // Helper function to get button class based on results
  const getButtonClass = (baseClass, isSelected, game, selection, isMoneyLine = true) => {
    let className = `${baseClass} ${isSelected ? 'selected' : ''}`;
    
    const locked = game.locked || new Date(game.start_time) <= new Date();
    
    if (locked && isSelected && activeGameResults[game.id]) {
      const actualResult = isMoneyLine 
        ? activeGameResults[game.id].winner 
        : activeGameResults[game.id].prop_result;
      
      if (actualResult) {
        const isCorrect = selection === actualResult;
        className += isCorrect ? ' correct' : ' incorrect';
      }
    }
    
    return className;
  };

  return (
    <div className="week-page-container">
      {/* Back button and refresh */}
      <div className="week-page-header">
        <button
          onClick={() => navigate(-1)}
          className="back-button"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="back-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className={`refresh-button ${isRefreshing ? 'refreshing' : ''}`}
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`refresh-icon ${isRefreshing ? 'spinning' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{isRefreshing ? 'Syncing...' : 'Sync'}</span>
        </button>
      </div>

      {/* Page title */}
      <h1 className="week-page-title">
        Week {weekNumber} Games
      </h1>

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
        <p className="no-games-text">
          No games available for this week.
        </p>
      ) : (
        <div className="games-grid">
          {weekGames.map((game, gameIndex) => {
            const { dayAndDate, formattedTime } = formatGameDateTime(game.start_time);
            const locked = game.locked || new Date(game.start_time) <= new Date();
            const hasResults = activeGameResults[game.id] ? true : false;

            return (
              <div 
                key={game.id} 
                className={`game-box ${locked ? 'locked' : ''} ${hasResults ? 'has-results' : ''}`}
              >
                {/* Money Line Section */}
                <div className="game-section money-line">
                  {/* Section result indicator */}
                  {getSectionResultIndicator(game, true, gameIndex)}
                  
                  {/* Date and time display */}
                  <div className="game-datetime">
                    <div className="date-line">{dayAndDate}</div>
                    <div className="time-line">{formattedTime}</div>
                  </div>

                  {/* Matchup display */}
                  <p className="matchup">
                    {game.away_team} @ {game.home_team}
                    {locked && <span className="lock-icon">🔒</span>}
                  </p>

                  {/* Team selection buttons */}
                  <div className="button-row">
                    <button
                      className={getButtonClass(
                        'team-button',
                        moneyLineSelections[game.id] === game.away_team,
                        game,
                        game.away_team,
                        true
                      )}
                      onClick={() => {
                        if (!locked) {
                          handleMoneyLineClick(game, game.away_team);
                        }
                      }}
                      disabled={locked}
                      aria-label={`Select ${game.away_team} to win`}
                    >
                      {game.away_team}
                    </button>
                    <button
                      className={getButtonClass(
                        'team-button',
                        moneyLineSelections[game.id] === game.home_team,
                        game,
                        game.home_team,
                        true
                      )}
                      onClick={() => {
                        if (!locked) {
                          handleMoneyLineClick(game, game.home_team);
                        }
                      }}
                      disabled={locked}
                      aria-label={`Select ${game.home_team} to win`}
                    >
                      {game.home_team}
                    </button>
                  </div>
                </div>

                {/* Divider line (only show if prop bets exist) */}
                {game.prop_bets && game.prop_bets.length > 0 && (
                  <div className="divider-line" />
                )}

                {/* Prop Bet Section */}
                {game.prop_bets && game.prop_bets.length > 0 && (
                  <div className="game-section prop-bet">
                    {/* Section result indicator */}
                    {getSectionResultIndicator(game, false, gameIndex)}
                    
                    <p className="prop-question">
                      {game.prop_bets[0].question}
                      {locked && <span className="lock-icon">🔒</span>}
                    </p>

                    {/* Prop bet option buttons */}
                    <div className="button-row">
                      {game.prop_bets[0].options.map((option, index) => (
                        <button
                          key={index}
                          className={getButtonClass(
                            'propbet-button',
                            propBetSelections[game.prop_bets[0].id] === option,
                            game,
                            option,
                            false
                          )}
                          onClick={() => {
                            if (!locked) {
                              handlePropBetClick(game, option);
                            }
                          }}
                          disabled={locked}
                          aria-label={`Select ${option} for prop bet`}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}