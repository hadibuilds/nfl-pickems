import React from 'react';
import UserAvatar from './UserAvatar';

export default function PeekPicksSection({ game, peekData }) {
  const propBet = game?.prop_bets?.[0];

  // Group users by their picks (backend shape you described)
  const picksByTeam = peekData?.moneyline_picks || { home_team: [], away_team: [] };
  const picksByProp = peekData?.prop_picks || { answer_a: [], answer_b: [] };

  const getOptionLabel = (answerKey) => {
    if (!propBet) return answerKey === 'answer_a' ? 'Option A' : 'Option B';
    const a = propBet.option_a ?? propBet.options?.[0] ?? 'Option A';
    const b = propBet.option_b ?? propBet.options?.[1] ?? 'Option B';
    return answerKey === 'answer_a' ? a : b;
  };

  // Determine correct choices based on game results
  const isAwayTeamCorrect = game.winner === game.away_team;
  const isHomeTeamCorrect = game.winner === game.home_team;
  const isAwayTeamIncorrect = game.winner && game.winner !== game.away_team;
  const isHomeTeamIncorrect = game.winner && game.winner !== game.home_team;
  
  // For prop bets, check if correct_answer matches the options
  const isPropACorrect = propBet?.correct_answer === getOptionLabel('answer_a');
  const isPropBCorrect = propBet?.correct_answer === getOptionLabel('answer_b');
  const isPropAIncorrect = propBet?.correct_answer && propBet?.correct_answer !== getOptionLabel('answer_a');
  const isPropBIncorrect = propBet?.correct_answer && propBet?.correct_answer !== getOptionLabel('answer_b');

  return (
    <>
      {/* Moneyline Section - mimics MoneyLineSection from GameCard */}
      <div className="moneyline-section">
        <div className="moneyline-grid">
          {/* Away Team */}
          <div className={`team-option away-team ${isAwayTeamCorrect ? 'correct' : ''} ${isAwayTeamIncorrect ? 'incorrect' : ''}`}>
            <div className="team-name">{game.away_team}</div>
            <div className="users-container">
              {(picksByTeam.away_team || []).length === 0 ? (
                <span className="no-picks">—</span>
              ) : (
                (picksByTeam.away_team || []).map((user) => (
                  <UserAvatar key={user.username} user={user} size={24} borderStyle="peek" />
                ))
              )}
            </div>
          </div>

          {/* Home Team */}
          <div className={`team-option home-team ${isHomeTeamCorrect ? 'correct' : ''} ${isHomeTeamIncorrect ? 'incorrect' : ''}`}>
            <div className="team-name">{game.home_team}</div>
            <div className="users-container">
              {(picksByTeam.home_team || []).length === 0 ? (
                <span className="no-picks">—</span>
              ) : (
                (picksByTeam.home_team || []).map((user) => (
                  <UserAvatar key={user.username} user={user} size={24} borderStyle="peek" />
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* PropBet Section - mimics PropBetSection from GameCard */}
      {propBet && (
        <>
          {/* Divider between sections */}
          <div className="divider-line" />
          
          <div className="propbet-section">
            <div className="propbet-question">
              {propBet.question}
            </div>
            
            <div className="propbet-grid">
              {/* Option A */}
              <div className={`prop-option option-a ${isPropACorrect ? 'correct' : ''} ${isPropAIncorrect ? 'incorrect' : ''}`}>
                <div className="option-name">{getOptionLabel('answer_a')}</div>
                <div className="users-container">
                  {(picksByProp.answer_a || []).length === 0 ? (
                    <span className="no-picks">—</span>
                  ) : (
                    (picksByProp.answer_a || []).map((user) => (
                      <UserAvatar key={user.username} user={user} size={24} />
                    ))
                  )}
                </div>
              </div>

              {/* Option B */}
              <div className={`prop-option option-b ${isPropBCorrect ? 'correct' : ''} ${isPropBIncorrect ? 'incorrect' : ''}`}>
                <div className="option-name">{getOptionLabel('answer_b')}</div>
                <div className="users-container">
                  {(picksByProp.answer_b || []).length === 0 ? (
                    <span className="no-picks">—</span>
                  ) : (
                    (picksByProp.answer_b || []).map((user) => (
                      <UserAvatar key={user.username} user={user} size={24} />
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
