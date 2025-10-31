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
          zIndex: 5
        }}>
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
            style={{ 
              filter: 'drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3))',
              opacity: 0.8
            }}
          >
            <path 
              d="M16 10V8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8V10M7 10C6.44772 10 6 10.4477 6 11V19C6 19.5523 6.44772 20 7 20H17C17.5523 20 18 19.5523 18 19V11C18 10.4477 17.5523 10 17 10H7Z" 
              stroke="#9CA3AF" 
              strokeWidth="1.8" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            />
            <circle 
              cx="12" 
              cy="15" 
              r="1.5" 
              fill="#6B7280"
            />
          </svg>
        </div>
      )}
      
      <div className="team-matchup">
        <span className="team-matchup-text">{game.away_team}</span>
        <span className="vs-separator">@</span>
        <span className="team-matchup-text">{game.home_team}</span>
      </div>
      
      <div className="game-details">
        <span className="game-time">{dayAndDate} • {formattedTime} PST</span>
      </div>
    </div>
  );
}