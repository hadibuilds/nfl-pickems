/*
 * Game Info Section Component
 * Top section of game card showing team matchup and game time
 */

import React from 'react';
import { formatGameDateTime, isGameLocked } from '../../utils/dateFormatters.js';

export default function GameInfoSection({ game }) {
  const { dayAndDate, formattedTime } = formatGameDateTime(game.start_time);
  const locked = isGameLocked(game.start_time, game.locked);

  return (
    <div className="game-info-section">
      {/* Lock icon */}
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
  );
}