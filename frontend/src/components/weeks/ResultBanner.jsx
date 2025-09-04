/*
ResultBanner.jsx
Enhanced progress indicator for GamePage showing live results tracking
Displays picks made, points scored, and accuracy breakdowns
CSS styles are in App.css

FIXES:
- Do NOT count prop-bets as "resolved" unless an actual answer exists (not null/undefined/empty)
- Robustly reads results from both shapes:
    moneyline: result.winner OR result.winning_team
    prop:      result.prop_result OR result.prop_bet_results[0].correct_answer (only if present)
- Uses only SAVED (submitted) picks to compute correctness
*/

import React from 'react';

// ---- helpers ---------------------------------------------------------------

const normalize = (v) => (typeof v === 'string' ? v.trim() : v);

const extractResults = (game, gameResults) => {
  const res = gameResults?.[game?.id] || {};

  // moneyline winner (alias + legacy)
  const winner =
    res?.winner != null && res.winner !== ''
      ? res.winner
      : res?.winning_team != null && res.winning_team !== ''
      ? res.winning_team
      : null;

  // prop result can be top-level or in array
  let prop = null;
  if (res && Object.prototype.hasOwnProperty.call(res, 'prop_result')) {
    const pr = res.prop_result;
    // treat empty string and null as "not resolved"
    if (pr !== null && pr !== undefined && String(pr).trim() !== '') {
      prop = pr;
    }
  } else if (Array.isArray(res?.prop_bet_results) && res.prop_bet_results.length === 1) {
    const ans = res.prop_bet_results[0]?.correct_answer;
    if (ans !== null && ans !== undefined && String(ans).trim() !== '') {
      prop = ans;
    }
  }

  return { winner, prop };
};

export default function ResultBanner({
  games,
  originalSubmittedPicks,    // saved moneyline picks by game.id
  originalSubmittedPropBets, // saved prop answers by prop_bet.id (first prop per game)
  gameResults = {},
}) {
  // Moneyline summary (uses SAVED picks only)
  const calculateMoneyLineResults = () => {
    const totalMoneyLineGames = games.length;

    const madeMoneyLineSelections = games.reduce((acc, g) => {
      return acc + (originalSubmittedPicks?.[g.id] ? 1 : 0);
    }, 0);

    // consider "with results" only when a winner exists
    const gamesWithResults = games.filter((g) => {
      const { winner } = extractResults(g, gameResults);
      return winner !== null && winner !== undefined && String(winner).trim() !== '';
    });

    const correctMoneyLinePicks = gamesWithResults.reduce((acc, g) => {
      const userPick = originalSubmittedPicks?.[g.id];
      const { winner } = extractResults(g, gameResults);
      if (!userPick || winner == null) return acc;
      return acc + (normalize(userPick) === normalize(winner) ? 1 : 0);
    }, 0);

    return {
      made: madeMoneyLineSelections,
      total: totalMoneyLineGames,
      correct: correctMoneyLinePicks,
      withResults: gamesWithResults.length,
      points: correctMoneyLinePicks * 1,
    };
  };

  // Prop summary (uses SAVED picks only; counts denominator ONLY when resolved)
  const calculatePropBetResults = () => {
    const gamesWithProps = games.filter((g) => Array.isArray(g.prop_bets) && g.prop_bets.length > 0);
    const totalPropSlots = gamesWithProps.length; // how many props were offered this week (first prop per game)

    const madePropSelections = gamesWithProps.reduce((acc, g) => {
      const firstPropId = g.prop_bets?.[0]?.id;
      return acc + (firstPropId && originalSubmittedPropBets?.[firstPropId] ? 1 : 0);
    }, 0);

    // count a prop "with result" ONLY when we have an actual answer value
    const propsWithResults = gamesWithProps.filter((g) => {
      const { prop } = extractResults(g, gameResults);
      return prop !== null && prop !== undefined && String(prop).trim() !== '';
    });

    const correctPropPicks = propsWithResults.reduce((acc, g) => {
      const firstPropId = g.prop_bets?.[0]?.id;
      if (!firstPropId) return acc;

      const userAnswer = originalSubmittedPropBets?.[firstPropId];
      const { prop } = extractResults(g, gameResults);

      if (!userAnswer || prop == null) return acc;
      return acc + (normalize(userAnswer) === normalize(prop) ? 1 : 0);
    }, 0);

    return {
      made: madePropSelections,
      total: totalPropSlots,          // total props offered (first-prop per game)
      correct: correctPropPicks,
      withResults: propsWithResults.length, // only resolved props
      points: correctPropPicks * 2,
    };
  };

  const calculateOverallProgress = () => {
    const ml = calculateMoneyLineResults();
    const pb = calculatePropBetResults();

    const totalPossiblePicks = ml.total + pb.total; // how many choices offered this week
    const totalMadePicks = ml.made + pb.made;
    const totalResolved = ml.withResults + pb.withResults;
    const totalPoints = ml.points + pb.points;

    return {
      made: totalMadePicks,
      total: totalPossiblePicks,
      gamesFinished: totalResolved,
      points: totalPoints,
    };
  };

  const ml = calculateMoneyLineResults();
  const pb = calculatePropBetResults();
  const overall = calculateOverallProgress();

  // Percentages (rounded to nearest whole)
  const mlPct = ml.withResults > 0 ? Math.round((ml.correct / ml.withResults) * 100) : 0;
  const pbPct = pb.withResults > 0 ? Math.round((pb.correct / pb.withResults) * 100) : 0;

  if (!Array.isArray(games) || games.length === 0) return null;

  return (
    <div className="result-banner">
      {/* Top Stats Row */}
      <div className="result-stats-row">
        <div className="stat-group">
          <span className="stat-label">Total Picks</span>
          <span className="stat-value">
            {overall.made}/{overall.total}
          </span>
        </div>
        <div className="stat-group">
          <span className="stat-label">Points Scored</span>
          <span className="stat-value points-value">{overall.points}</span>
        </div>
      </div>

      {/* Results Breakdown */}
      <div className="results-breakdown">
        {/* Money Line Section */}
        <div className="result-section">
          <div className="result-section-header">
            <span>Money Line</span>
            <span className="correct-fraction">
              {ml.correct}/{ml.withResults}
              {ml.withResults > 0 && ` (${mlPct}%)`}
            </span>
          </div>
          <div className="result-progress-bar">
            <div className="result-progress-fill moneyline-fill" style={{ width: `${mlPct}%` }} />
          </div>
        </div>

        {/* Prop Bets Section */}
        <div className="result-section">
          <div className="result-section-header">
            <span>Prop Bets</span>
            <span className="correct-fraction">
              {pb.correct}/{pb.withResults}
              {pb.withResults > 0 && ` (${pbPct}%)`}
            </span>
          </div>
          <div className="result-progress-bar">
            <div className="result-progress-fill propbet-fill" style={{ width: `${pbPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
