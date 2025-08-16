/*
 * Game Helper Utilities
 * Contains game-related logic for button classes, prediction badges, etc.
 * FIXED: Changed to .jsx file since it contains JSX components
 */

import React from 'react';
import { isGameLocked } from './dateFormatters.js';

/**
 * Get CSS class for team/prop bet buttons based on selection and results
 * @param {string} baseClass - Base CSS class
 * @param {boolean} isSelected - Whether button is selected
 * @param {Object} game - Game object
 * @param {string} selection - Current selection value
 * @param {Object} gameResults - Game results object
 * @param {boolean} isMoneyLine - Whether this is money line (vs prop bet)
 * @returns {string} - Complete CSS class string
 */
export const getButtonClass = (baseClass, isSelected, game, selection, gameResults, isMoneyLine = true) => {
  let className = `${baseClass} ${isSelected ? 'selected' : ''}`;
  
  const locked = isGameLocked(game.start_time, game.locked);
  
  if (locked && isSelected && gameResults[game.id]) {
    const actualResult = isMoneyLine 
      ? gameResults[game.id].winner 
      : gameResults[game.id].prop_result;
    
    if (actualResult) {
      const isCorrect = selection === actualResult;
      className += isCorrect ? ' correct' : ' incorrect';
    }
  }
  
  return className;
};

/**
 * Get correct prediction badge component (only shows for correct predictions)
 * @param {Object} game - Game object
 * @param {boolean} isMoneyLineSection - Whether this is money line section
 * @param {Object} moneyLineSelections - Money line selections
 * @param {Object} propBetSelections - Prop bet selections
 * @param {Object} gameResults - Game results
 * @returns {JSX.Element|null} - Badge component or null
 */
export const getCorrectPredictionBadge = (game, isMoneyLineSection, moneyLineSelections, propBetSelections, gameResults) => {
  if (!gameResults[game.id]) return null;

  let userSelection, actualResult, points;

  if (isMoneyLineSection) {
    userSelection = moneyLineSelections[game.id];
    actualResult = gameResults[game.id].winner;
    points = 1; // 1pt for money line
  } else {
    if (!game.prop_bets || game.prop_bets.length === 0) return null;
    userSelection = propBetSelections[game.prop_bets[0].id];
    actualResult = gameResults[game.id].prop_result;
    points = 2; // 2pts for prop bet
  }

  if (!userSelection || !actualResult) return null;

  const isCorrect = userSelection === actualResult;

  // Only show badge if prediction is correct
  if (isCorrect) {
    return (
      <div className="points-badge correct-prediction">
        {points}pt{points > 1 ? 's' : ''}
      </div>
    );
  }

  // Return nothing if incorrect
  return null;
};

/**
 * Check if game has results
 * @param {Object} game - Game object
 * @param {Object} gameResults - Game results object
 * @returns {boolean} - Whether game has results
 */
export const gameHasResults = (game, gameResults) => {
  return gameResults[game.id] ? true : false;
};

/**
 * Get game status string
 * @param {Object} game - Game object
 * @param {Object} gameResults - Game results object
 * @returns {string} - Status: 'upcoming', 'locked', 'completed'
 */
export const getGameStatus = (game, gameResults) => {
  if (gameHasResults(game, gameResults)) return 'completed';
  if (isGameLocked(game.start_time, game.locked)) return 'locked';
  return 'upcoming';
};