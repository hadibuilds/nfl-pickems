/*
 * Game Helper Utilities
 * Contains game-related logic for button classes, prediction badges, etc.
 * FIXED/ROBUST:
 *  - Supports both `winner` and legacy `winning_team`
 *  - Supports `prop_result` and fallback to first `prop_bet_results[0].correct_answer`
 *  - Safe guards when props are missing or when there are multiple props
 */

import React from 'react';
import { isGameLocked } from './dateFormatters.js';

// Points constants (single source of truth)
const MONEYLINE_POINTS = 1;
const PROP_POINTS = 2;

/** Normalize primitive values for safe comparisons */
const normalize = (v) => (typeof v === 'string' ? v.trim() : v);

/**
 * Extract the authoritative results for a given game from the `gameResults` map.
 * Supports both new and legacy backend shapes.
 * @param {Object} game - Game object (must contain `id` and optional `prop_bets`)
 * @param {Object} gameResults - Results map keyed by game.id
 * @returns {{ moneyline: any, prop: any }} - Extracted results
 */
export const extractGameOutcome = (game, gameResults) => {
  const res = gameResults?.[game?.id] ?? {};

  // Moneyline result: prefer `winner`, fallback to legacy `winning_team`
  const moneyline =
    res.winner !== undefined && res.winner !== null
      ? res.winner
      : res.winning_team !== undefined && res.winning_team !== null
      ? res.winning_team
      : null;

  // Prop result:
  // 1) Prefer top-level alias `prop_result`
  // 2) Fallback to first prop's correct answer if exactly one exists
  let prop = null;
  if (res.prop_result !== undefined && res.prop_result !== null) {
    prop = res.prop_result;
  } else if (Array.isArray(res.prop_bet_results) && res.prop_bet_results.length === 1) {
    prop = res.prop_bet_results[0]?.correct_answer ?? null;
  } else {
    // If there are multiple props, no single "prop_result" applies; leave null.
    prop = null;
  }

  return { moneyline, prop };
};

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
export const getButtonClass = (
  baseClass,
  isSelected,
  game,
  selection,
  gameResults,
  isMoneyLine = true
) => {
  let className = `${baseClass} ${isSelected ? 'selected' : ''}`;
  const locked = isGameLocked(game?.start_time, game?.locked);

  if (locked && isSelected) {
    const { moneyline, prop } = extractGameOutcome(game, gameResults);
    const actualResult = isMoneyLine ? moneyline : prop;

    if (actualResult !== null && actualResult !== undefined) {
      const isCorrect = normalize(selection) === normalize(actualResult);
      className += isCorrect ? ' correct' : ' incorrect';
    }
  }

  return className;
};

/**
 * Get correct prediction badge component (only shows for correct predictions)
 * @param {Object} game - Game object
 * @param {boolean} isMoneyLineSection - Whether this is money line section
 * @param {Object} moneyLineSelections - Money line selections map
 * @param {Object} propBetSelections - Prop bet selections map
 * @param {Object} gameResults - Game results
 * @returns {JSX.Element|null} - Badge component or null
 */
export const getCorrectPredictionBadge = (
  game,
  isMoneyLineSection,
  moneyLineSelections,
  propBetSelections,
  gameResults
) => {
  if (!game || !gameResults || !gameResults[game.id]) return null;

  const { moneyline, prop } = extractGameOutcome(game, gameResults);

  let userSelection, actualResult, points;

  if (isMoneyLineSection) {
    userSelection = moneyLineSelections?.[game.id];
    actualResult = moneyline;
    points = MONEYLINE_POINTS;
  } else {
    // Only support a single tracked prop in the banner (first prop), like FE expects
    const firstPropId = game?.prop_bets?.[0]?.id;
    if (!firstPropId) return null;

    userSelection = propBetSelections?.[firstPropId];
    actualResult = prop;
    points = PROP_POINTS;
  }

  if (userSelection == null || actualResult == null) return null;

  const isCorrect = normalize(userSelection) === normalize(actualResult);

  if (isCorrect) {
    return (
      <div className="points-badge correct-prediction">
        {points}pt{points > 1 ? 's' : ''}
      </div>
    );
  }

  return null;
};

/**
 * Determine if a game has results available (moneyline + prop, if applicable)
 * @param {Object} game - Game object
 * @param {Object} gameResults - Game results object
 * @returns {boolean}
 */
export const gameHasResults = (game, gameResults) => {
  const { moneyline, prop } = extractGameOutcome(game, gameResults);

  // If there are no props configured for this game, moneyline alone resolves it
  const hasPropsConfigured = Array.isArray(game?.prop_bets) && game.prop_bets.length > 0;

  if (!hasPropsConfigured) {
    return moneyline != null; // completed when winner is known
  }

  // When there is (exactly one) tracked prop in the UI, consider completed only when both are known
  // (If you later support multi-prop per gamecard, adjust this to your desired semantics.)
  return moneyline != null && prop != null;
};

/**
 * Get game status string
 * @param {Object} game - Game object
 * @param {Object} gameResults - Game results object
 * @returns {string} - 'upcoming' | 'locked' | 'completed'
 */
export const getGameStatus = (game, gameResults) => {
  if (gameHasResults(game, gameResults)) return 'completed';
  if (isGameLocked(game?.start_time, game?.locked)) return 'locked';
  return 'upcoming';
};
