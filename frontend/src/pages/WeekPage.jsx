/*
 * UPDATED: Enhanced WeekPage Component with Real-time Save Feedback
 * Features: Spinner and saved animations replace points badges during save operations
 * - Spinner shows during API POST request
 * - Brief saved animation confirms database update
 * - Points badges removed (CSS preserved for future correct prediction display)
 */

import React, { useState } from 'react';
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

  // Save state management for real-time feedback
  const [saveStates, setSaveStates] = useState({});
  // Format: { 'gameId-moneyline': 'saving'|'saved'|'error', 'gameId-propbet': 'saving'|'saved'|'error' }

  const [saveTimeouts, setSaveTimeouts] = useState({});

  // Use real results from backend
  const activeGameResults = gameResults;

  // Helper function to get team logo URL from GitHub (for abbreviations from database)
  const getTeamLogo = (teamAbbr) => {
    const teamLogos = {
      // Map abbreviations to mascot filenames
      'ARI': 'cardinals.png',
      'ATL': 'falcons.png',
      'BAL': 'ravens.png',
      'BUF': 'bills.png',
      'CAR': 'panthers.png',
      'CHI': 'bears.png',
      'CIN': 'bengals.png',
      'CLE': 'browns.png',
      'DAL': 'cowboys.png',
      'DEN': 'broncos.png',
      'DET': 'lions.png',
      'GB': 'packers.png',
      'HOU': 'texans.png',
      'IND': 'colts.png',
      'JAX': 'jaguars.png',
      'KC': 'chiefs.png',
      'LV': 'raiders.png',
      'LAC': 'chargers.png',
      'LAR': 'rams.png',
      'MIA': 'dolphins.png',
      'MIN': 'vikings.png',
      'NE': 'patriots.png',
      'NO': 'saints.png',
      'NYG': 'giants.png',
      'NYJ': 'jets.png',
      'PHI': 'eagles.png',
      'PIT': 'steelers.png',
      'SF': '49ers.png',
      'SEA': 'seahawks.png',
      'TB': 'buccaneers.png',
      'TEN': 'titans.png',
      'WAS': 'commanders.png'
    };

    const logoFile = teamLogos[teamAbbr];
    if (logoFile) {
      return `https://raw.githubusercontent.com/hadibuilds/team-logos/master/NFL/${logoFile}`;
    }
    
    // Fallback: if abbreviation not found, try lowercase
    console.warn(`No logo found for team abbreviation: ${teamAbbr}`);
    return `https://raw.githubusercontent.com/hadibuilds/team-logos/master/NFL/${teamAbbr.toLowerCase()}.png`;
  };

  // Helper function to format date and time in PST
  const formatGameDateTime = (startTime) => {
    const gameDate = new Date(startTime);
    
    const pstOptions = {
      timeZone: 'America/Los_Angeles',
      weekday: 'short',
      month: '2-digit',
      day: '2-digit',
    };
    
    const timeOptions = {
      timeZone: 'America/Los_Angeles',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    };
    
    const dayAndDate = gameDate.toLocaleDateString('en-US', pstOptions);
    const formattedTime = gameDate.toLocaleTimeString('en-US', timeOptions);
    
    return { dayAndDate, formattedTime };
  };

  // Helper function to get section result indicator (checkmarks)
  const getSectionResultIndicator = (game, isMoneyLineSection) => {
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
      <div className={`checkmark ${isCorrect ? 'correct' : 'incorrect'}`}>
        {isCorrect ? '✓' : '✗'}
      </div>
    );
  };

  // Helper function to get save state indicator (spinner/saved/error)
  const getSaveStateIndicator = (game, isMoneyLineSection) => {
    const stateKey = `${game.id}-${isMoneyLineSection ? 'moneyline' : 'propbet'}`;
    const saveState = saveStates[stateKey];
    
    if (!saveState) return null;
    
    switch (saveState) {
      case 'saving':
        return (
          <div className="save-spinner">
            <div className="spinner-icon">⟳</div>
          </div>
        );
      case 'saved':
        return (
          <div className="save-success">
            <div className="saved-icon">✓</div>
          </div>
        );
      case 'error':
        return (
          <div className="save-error">
            <div className="error-icon">⚠</div>
          </div>
        );
      default:
        return null;
    }
  };
  // Enhanced money line click handler with save feedback
  const handleMoneyLineClickWithFeedback = async (game, team) => {
    if (game.locked) return;
    
    const stateKey = `${game.id}-moneyline`;
    
    // Clear any existing timeout for this section
    if (saveTimeouts[stateKey]) {
      clearTimeout(saveTimeouts[stateKey]);
      setSaveTimeouts(prev => {
        const newTimeouts = { ...prev };
        delete newTimeouts[stateKey];
        return newTimeouts;
      });
    }
    
    try {
      // Show spinner
      setSaveStates(prev => ({ ...prev, [stateKey]: 'saving' }));
      
      // Ensure spinner shows for at least 1 second, even if API is faster
      await Promise.all([
        handleMoneyLineClick(game, team),
        new Promise(resolve => setTimeout(resolve, 1000))
      ]);
      
      // Show saved state
      setSaveStates(prev => ({ ...prev, [stateKey]: 'saved' }));
      
      // Set new timeout and track it
      const timeoutId = setTimeout(() => {
        setSaveStates(prev => {
          const newState = { ...prev };
          delete newState[stateKey];
          return newState;
        });
        setSaveTimeouts(prev => {
          const newTimeouts = { ...prev };
          delete newTimeouts[stateKey];
          return newTimeouts;
        });
      }, 2000);
      
      setSaveTimeouts(prev => ({ ...prev, [stateKey]: timeoutId }));
      
    } catch (error) {
      // Show error state
      setSaveStates(prev => ({ ...prev, [stateKey]: 'error' }));
      
      // Set error timeout and track it
      const timeoutId = setTimeout(() => {
        setSaveStates(prev => {
          const newState = { ...prev };
          delete newState[stateKey];
          return newState;
        });
        setSaveTimeouts(prev => {
          const newTimeouts = { ...prev };
          delete newTimeouts[stateKey];
          return newTimeouts;
        });
      }, 3000);
      
      setSaveTimeouts(prev => ({ ...prev, [stateKey]: timeoutId }));
      
      console.error('Failed to save money line selection:', error);
    }
  };

  // Enhanced prop bet click handler with save feedback
  const handlePropBetClickWithFeedback = async (game, answer) => {
    if (game.locked) return;
    
    const stateKey = `${game.id}-propbet`;
    
    // Clear any existing timeout for this section
    if (saveTimeouts[stateKey]) {
      clearTimeout(saveTimeouts[stateKey]);
      setSaveTimeouts(prev => {
        const newTimeouts = { ...prev };
        delete newTimeouts[stateKey];
        return newTimeouts;
      });
    }
    
    try {
      // Show spinner
      setSaveStates(prev => ({ ...prev, [stateKey]: 'saving' }));
      
      // Ensure spinner shows for at least 1 second, even if API is faster
      await Promise.all([
        handlePropBetClick(game, answer),
        new Promise(resolve => setTimeout(resolve, 1000))
      ]);
      
      // Show saved state
      setSaveStates(prev => ({ ...prev, [stateKey]: 'saved' }));
      
      // Set new timeout and track it
      const timeoutId = setTimeout(() => {
        setSaveStates(prev => {
          const newState = { ...prev };
          delete newState[stateKey];
          return newState;
        });
        setSaveTimeouts(prev => {
          const newTimeouts = { ...prev };
          delete newTimeouts[stateKey];
          return newTimeouts;
        });
      }, 2000);
      
      setSaveTimeouts(prev => ({ ...prev, [stateKey]: timeoutId }));
      
    } catch (error) {
      // Show error state
      setSaveStates(prev => ({ ...prev, [stateKey]: 'error' }));
      
      // Set error timeout and track it
      const timeoutId = setTimeout(() => {
        setSaveStates(prev => {
          const newState = { ...prev };
          delete newState[stateKey];
          return newState;
        });
        setSaveTimeouts(prev => {
          const newTimeouts = { ...prev };
          delete newTimeouts[stateKey];
          return newTimeouts;
        });
      }, 3000);
      
      setSaveTimeouts(prev => ({ ...prev, [stateKey]: timeoutId }));
      
      console.error('Failed to save prop bet selection:', error);
    }
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
    <div className="pt-16 px-4">
      {/* Back button and refresh */}
      <div className="flex justify-between items-center mb-6">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#3a3a3a] transition"
          style={{ backgroundColor: '#2d2d2d' }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl text-white hover:bg-[#1d4ed8] transition disabled:opacity-50"
          style={{ backgroundColor: '#2d2d2d' }}
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{isRefreshing ? 'Sync' : 'Sync'}</span>
        </button>
      </div>

      {/* Page title */}
      <h1 className="text-4xl text-center mb-8 text-white">
        Week {weekNumber} Games
      </h1>

      {/* Scaled content */}
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
            {weekGames.map((game, gameIndex) => {
              const { dayAndDate, formattedTime } = formatGameDateTime(game.start_time);
              const locked = game.locked || new Date(game.start_time) <= new Date();
              const hasResults = activeGameResults[game.id] ? true : false;

              return (
                <div 
                  key={game.id} 
                  className={`game-box ${locked ? 'locked' : ''} ${hasResults ? 'has-results' : ''}`}
                >
                  {/* TOP SECTION - Game Info Only */}
                  <div className="game-info-section">
                    {/* Lock icon - positioned like points badges in other sections */}
                    {locked && (
                      <div style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        color: '#888',
                        fontSize: '16px',
                        zIndex: 5
                      }}>
                        🔒
                      </div>
                    )}
                    
                    <div className="team-matchup">
                      <span className="team-matchup-text">{game.away_team}</span>
                      <span className="vs-separator">vs</span>
                      <span className="team-matchup-text">{game.home_team}</span>
                    </div>
                    
                    <div className="game-details">
                      <span className="game-time">{dayAndDate} • {formattedTime} PST</span>
                    </div>
                  </div>

                  {/* DIVIDER */}
                  <div className="divider-line" />

                  {/* MIDDLE SECTION - Money Line */}
                  <div className="game-section money-line">
                    {/* Save state indicator (replaces points badge) */}
                    {getSaveStateIndicator(game, true)}
                    
                    {/* Checkmark for results */}
                    {getSectionResultIndicator(game, true)}
                    
                    {/* Team buttons with logos */}
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
                            handleMoneyLineClickWithFeedback(game, game.away_team);
                          }
                        }}
                        disabled={locked}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: '8px'
                        }}
                      >
                        <img 
                          src={getTeamLogo(game.away_team)} 
                          alt={`${game.away_team} logo`}
                          style={{
                            width: '48px',
                            height: '48px',
                            objectFit: 'contain'
                          }}
                          onError={(e) => e.target.style.display = 'none'}
                        />
                        <span style={{fontSize: '0.8rem', fontWeight: '600'}}>{game.away_team}</span>
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
                            handleMoneyLineClickWithFeedback(game, game.home_team);
                          }
                        }}
                        disabled={locked}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: '8px'
                        }}
                      >
                        <img 
                          src={getTeamLogo(game.home_team)} 
                          alt={`${game.home_team} logo`}
                          style={{
                            width: '48px',
                            height: '48px',
                            objectFit: 'contain'
                          }}
                          onError={(e) => e.target.style.display = 'none'}
                        />
                        <span style={{fontSize: '0.8rem', fontWeight: '600'}}>{game.home_team}</span>
                      </button>
                    </div>
                  </div>

                  {/* DIVIDER (only if prop bets exist) */}
                  {game.prop_bets && game.prop_bets.length > 0 && (
                    <div className="divider-line" />
                  )}

                  {/* BOTTOM SECTION - Prop Bet */}
                  {game.prop_bets && game.prop_bets.length > 0 && (
                    <div className="game-section prop-bet">
                      {/* Save state indicator (replaces points badge) */}
                      {getSaveStateIndicator(game, false)}
                      
                      {/* Checkmark for results */}
                      {getSectionResultIndicator(game, false)}
                      
                      <p className="prop-question">
                        {game.prop_bets[0].question}
                      </p>

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
                                handlePropBetClickWithFeedback(game, option);
                              }
                            }}
                            disabled={locked}
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
    </div>
  );
}