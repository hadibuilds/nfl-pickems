import React from 'react';
import GameInfoSection from '../game/GameInfoSection';
import PeekPicksSection from './PeekPicksSection';

export default function PeekGameCard({ game, peekData }) {
  return (
    <div
      className="game-box locked"
      style={{
        border: '1px solid rgba(68, 68, 68, 0.4)',
        borderRadius: '16px',
        backgroundColor: '#101118',
        overflow: 'hidden',
        boxShadow: '0 18px 45px rgba(0, 0, 0, 0.8)'
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