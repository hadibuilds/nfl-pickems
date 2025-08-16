/*
 * Prop Bet Section Component
 * Bottom section of game card with prop bet options
 */

import React from 'react';
import { getButtonClass, getCorrectPredictionBadge } from '../../utils/gameHelpers.jsx';
import { isGameLocked } from '../../utils/dateFormatters.js';
import SaveStateIndicator from './SaveStateIndicator.jsx';

export default function PropBetSection({ 
  game, 
  moneyLineSelections,
  propBetSelections, 
  gameResults,
  onPropBetClick,
  saveStateManager
}) {
  // Early return if no prop bets
  if (!game.prop_bets || game.prop_bets.length === 0) {
    return null;
  }

  const locked = isGameLocked(game.start_time, game.locked);
  const stateKey = saveStateManager.generateStateKey(game.id, 'propbet');
  const saveState = saveStateManager.getSaveState(stateKey);
  const propBet = game.prop_bets[0];

  const handlePropBetClick = async (answer) => {
    if (locked) return;
    
    try {
      saveStateManager.setSaving(stateKey);
      
      // Ensure spinner shows for at least 500ms
      await Promise.all([
        onPropBetClick(game, answer),
        new Promise(resolve => setTimeout(resolve, 500))
      ]);
      
      saveStateManager.setSaved(stateKey);
    } catch (error) {
      saveStateManager.setError(stateKey);
      console.error('Failed to save prop bet selection:', error);
    }
  };

  return (
    <>
      {/* Divider */}
      <div className="divider-line" />
      
      {/* Prop bet section */}
      <div className="game-section prop-bet">
        {/* Save state indicator */}
        <SaveStateIndicator saveState={saveState} />
        
        {/* Correct prediction badge */}
        {getCorrectPredictionBadge(game, false, moneyLineSelections, propBetSelections, gameResults)}
        
        <p className="prop-question">
          {propBet.question}
        </p>

        <div className="button-row">
          {propBet.options.map((option, index) => (
            <button
              key={index}
              className={getButtonClass(
                'propbet-button',
                propBetSelections[propBet.id] === option,
                game,
                option,
                gameResults,
                false
              )}
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