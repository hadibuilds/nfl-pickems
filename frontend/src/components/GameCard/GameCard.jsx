/*
 * Game Card Component - CLEANED
 * Main wrapper for individual game cards
 * Combines all sections: info, money line, and prop bets
 * 🧹 REMOVED: Save state manager dependency
 */

import React from 'react';
import GameInfoSection from './GameInfoSection.jsx';
import MoneyLineSection from './MoneyLineSection.jsx';
import PropBetSection from './PropBetSection.jsx';
import { gameHasResults } from '../../utils/gameHelpers.jsx';
import { isGameLocked } from '../../utils/dateFormatters.js';

export default function GameCard({
  game,
  moneyLineSelections,
  propBetSelections,
  gameResults,
  onMoneyLineClick,
  onPropBetClick
}) {
  const locked = isGameLocked(game.start_time, game.locked);
  const hasResults = gameHasResults(game, gameResults);

  return (
    <div 
      className={`game-box ${locked ? 'locked' : ''} ${hasResults ? 'has-results' : ''}`}
    >
      {/* Top section - Game info */}
      <GameInfoSection game={game} />

      {/* Divider */}
      <div className="divider-line" />

      {/* Middle section - Money line */}
      <MoneyLineSection
        game={game}
        moneyLineSelections={moneyLineSelections}
        propBetSelections={propBetSelections}
        gameResults={gameResults}
        onTeamClick={onMoneyLineClick}
      />

      {/* Bottom section - Prop bets (conditional) */}
      <PropBetSection
        game={game}
        moneyLineSelections={moneyLineSelections}
        propBetSelections={propBetSelections}
        gameResults={gameResults}
        onPropBetClick={onPropBetClick}
      />
    </div>
  );
}