import React from 'react';
import GameInfoSection from '../game/GameInfoSection';
import PeekPicksSection from './PeekPicksSection';

export default function PeekGameCard({ game, peekData }) {
  return (
    <div
      className="game-box locked"
      style={{
        border: '1px solid rgba(68, 68, 68, 0.4)',
        borderRadius: '8px',
        backgroundColor: '#2d2d2d',
        overflow: 'hidden',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(68, 68, 68, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.08)'
      }}
    >
      {/* Top section - Game info (reuse existing component) */}
      <GameInfoSection game={game} />

      {/* Divider */}
      <div className="divider-line" />

      {/* Peek picks section - 4 quadrants layout */}
      <PeekPicksSection 
        game={game} 
        peekData={peekData}
      />
    </div>
  );
}