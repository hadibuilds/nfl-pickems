/*
 * Game Card Component - CLEANED
 * Main wrapper for individual game cards
 * Combines all sections: info, money line, and prop bets
 * 🧹 REMOVED: Save state manager dependency
 * 🆕 DRAFT STYLING: Yellow border for unsubmitted picks
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
  onPropBetClick,
  // 🆕 DRAFT TRACKING: Props for determining draft state
  originalSubmittedPicks = {},
  originalSubmittedPropBets = {},
  draftPicks = {},
  draftPropBets = {}
}) {
  const locked = isGameLocked(game.start_time, game.locked);
  const hasResults = gameHasResults(game, gameResults);

  // 🆕 DRAFT STATE: Check if money line pick is in draft state
  const isMoneyLineDraft = draftPicks[game.id] && 
    draftPicks[game.id] !== originalSubmittedPicks[game.id];

  // 🆕 DRAFT STATE: Check if prop bet pick is in draft state
  const propBetId = game.prop_bets?.[0]?.id;
  const isPropBetDraft = propBetId && 
    draftPropBets[propBetId] && 
    draftPropBets[propBetId] !== originalSubmittedPropBets[propBetId];

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
        isDraft={isMoneyLineDraft}
      />

      {/* Bottom section - Prop bets (conditional) */}
      <PropBetSection
        game={game}
        moneyLineSelections={moneyLineSelections}
        propBetSelections={propBetSelections}
        gameResults={gameResults}
        onPropBetClick={onPropBetClick}
        isDraft={isPropBetDraft}
      />
    </div>
  );
}