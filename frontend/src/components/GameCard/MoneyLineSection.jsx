/*
 * Money Line Section Component
 * Middle section of game card with team selection buttons
 */

import React from 'react';
import { getTeamLogo } from '../../utils/teamLogos.js';
import { getButtonClass, getCorrectPredictionBadge } from '../../utils/gameHelpers.jsx';
import { isGameLocked } from '../../utils/dateFormatters.js';
import SaveStateIndicator from './SaveStateIndicator.jsx';

export default function MoneyLineSection({ 
  game, 
  moneyLineSelections, 
  propBetSelections,
  gameResults,
  onTeamClick,
  saveStateManager
}) {
  const locked = isGameLocked(game.start_time, game.locked);
  const stateKey = saveStateManager.generateStateKey(game.id, 'moneyline');
  const saveState = saveStateManager.getSaveState(stateKey);

  const handleTeamClick = async (team) => {
    if (locked) return;
    
    try {
      saveStateManager.setSaving(stateKey);
      
      // Ensure spinner shows for at least 500ms
      await Promise.all([
        onTeamClick(game, team),
        new Promise(resolve => setTimeout(resolve, 500))
      ]);
      
      saveStateManager.setSaved(stateKey);
    } catch (error) {
      saveStateManager.setError(stateKey);
      console.error('Failed to save money line selection:', error);
    }
  };

  return (
    <div className="game-section money-line">
      {/* Save state indicator */}
      <SaveStateIndicator saveState={saveState} />
      
      {/* Correct prediction badge */}
      {getCorrectPredictionBadge(game, true, moneyLineSelections, propBetSelections, gameResults)}
      
      {/* Team buttons with logos */}
      <div className="button-row">
        <button
          className={getButtonClass(
            'team-button',
            moneyLineSelections[game.id] === game.away_team,
            game,
            game.away_team,
            gameResults,
            true
          )}
          onClick={() => handleTeamClick(game.away_team)}
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
            gameResults,
            true
          )}
          onClick={() => handleTeamClick(game.home_team)}
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
  );
}