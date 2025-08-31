/*
 * Money Line Section Component - CLEANED
 * Middle section of game card with team selection buttons
 * 🧹 REMOVED: Save state indicators (spinners/checkmarks)
 * ✅ ENHANCED: Simple click handler with immediate visual feedback
 * 🆕 DRAFT STYLING: Yellow border for unsubmitted picks
 */

import React from 'react';
import { getTeamLogo } from '../../utils/teamLogos.js';
import { getButtonClass, getCorrectPredictionBadge } from '../../utils/gameHelpers.jsx';
import { isGameLocked } from '../../utils/dateFormatters.js';

export default function MoneyLineSection({ 
  game, 
  moneyLineSelections, 
  propBetSelections,
  gameResults,
  onTeamClick,
  isDraft = false // 🆕 DRAFT STATE: Whether this section has draft picks
}) {
  const locked = isGameLocked(game.start_time, game.locked);

  const handleTeamClick = async (team) => {
    if (locked) return;
    
    // Simple call - immediate visual feedback via state update
    await onTeamClick(game, team);
  };

  return (
    <div className="game-section money-line">
      
      {/* Team buttons with logos */}
      <div className="button-row">
        <button
          className={`${getButtonClass(
            'team-button',
            moneyLineSelections[game.id] === game.away_team,
            game,
            game.away_team,
            gameResults,
            true
          )} ${isDraft && moneyLineSelections[game.id] === game.away_team ? 'draft' : ''}`}
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
              width: '65px',
              height: '65px',
              objectFit: 'contain'
            }}
            onError={(e) => e.target.style.display = 'none'}
          />
          <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>
            {game.away_team}
          </span>
        </button>

        <button
          className={`${getButtonClass(
            'team-button',
            moneyLineSelections[game.id] === game.home_team,
            game,
            game.home_team,
            gameResults,
            true
          )} ${isDraft && moneyLineSelections[game.id] === game.home_team ? 'draft' : ''}`}
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
              width: '65px',
              height: '65px',
              objectFit: 'contain'
            }}
            onError={(e) => e.target.style.display = 'none'}
          />
          <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>
            {game.home_team}
          </span>
        </button>
      </div>
    </div>
  );
}