import React from 'react';
import GameInfoSection from '../game/GameInfoSection';
import PeekPicksSection from './PeekPicksSection';

export default function PeekGameCard({ game, peekData }) {
  return (
    <div 
      className="game-box locked"
      style={{
        border: '1px solid #444',
        borderRadius: '8px',
        backgroundColor: '#2d2d2d',
        overflow: 'hidden'
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