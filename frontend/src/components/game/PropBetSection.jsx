/*
 * Prop Bet Section Component - CLEANED
 * Bottom section of game card with prop bet options
 * 🧹 REMOVED: Save state indicators (spinners/checkmarks)
 * ✅ ENHANCED: Simple click handler with immediate visual feedback
 * 🆕 DRAFT STYLING: Yellow border for unsubmitted picks
 */

import React from 'react';
import { getButtonClass, getCorrectPredictionBadge } from '../../utils/gameHelpers.jsx';
import { isGameLocked } from '../../utils/dateFormatters.js';

export default function PropBetSection({ 
  game, 
  moneyLineSelections,
  propBetSelections, 
  gameResults,
  onPropBetClick,
  isDraft = false // 🆕 DRAFT STATE: Whether this section has draft picks
}) {
  // Early return if no prop bets
  if (!game.prop_bets || game.prop_bets.length === 0) {
    return null;
  }

  const locked = isGameLocked(game.start_time, game.locked);
  const propBet = game.prop_bets[0];

  const handlePropBetClick = async (answer) => {
    if (locked) return;
    
    // Simple call - immediate visual feedback via state update
    await onPropBetClick(game, answer);
  };

  return (
    <>
      {/* Divider */}
      <div className="divider-line" />
      
      {/* Prop bet section */}
      <div className="game-section prop-bet">
        {/* Correct prediction badge (keep for results display) */}
        {getCorrectPredictionBadge(game, false, moneyLineSelections, propBetSelections, gameResults)}
        
        <p className="prop-question">
          {propBet.question}
        </p>

        <div className="button-row">
          {propBet.options.map((option, index) => (
            <button
              key={index}
              className={`${getButtonClass(
                'propbet-button',
                propBetSelections[propBet.id] === option,
                game,
                option,
                gameResults,
                false
              )} ${isDraft && propBetSelections[propBet.id] === option ? 'draft' : ''}`}
              onClick={() => handlePropBetClick(option)}
              disabled={locked}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}