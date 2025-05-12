import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function WeekPage({
  games,
  moneyLineSelections,
  propBetSelections,
  handleMoneyLineClick,
  handlePropBetClick
}) {
  const { weekNumber } = useParams();
  const navigate = useNavigate();
  const weekGames = games.filter(game => game.week === parseInt(weekNumber));

  return (
    <div className="pt-16 px-4">
      <div className="flex justify-start mb-6">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-2xl bg-gray-100 dark:bg-[#2d2d2d] text-gray-800 dark:text-white hover:bg-gray-200 dark:hover:bg-[#3a3a3a] transition"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
      <h1 className="text-4xl text-center mb-8">Week {weekNumber} Games</h1>
      {weekGames.length === 0 ? (
        <p className="text-center">No games available for this week.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {weekGames.map((game) => {
            const startTime = new Date(game.start_time);
            const dayAndDate = startTime.toLocaleDateString('en-US', {
              weekday: 'short',
              month: '2-digit',
              day: '2-digit',
            });
            const formattedTime = startTime.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: true,
            });

            return (
              <div key={game.id} className="game-box">
                <div className="game-section money-line">
                  <div className="game-datetime">
                    <div className="date-line">{dayAndDate}</div>
                    <div className="time-line">{formattedTime}</div>
                  </div>
                  <p className="matchup">
                    {game.away_team} @ {game.home_team}{' '}
                    {game.locked && <span className="ml-2 text-gray-500">🔒</span>}
                  </p>
                  <div className="button-row">
                    <button
                      className={`team-button ${moneyLineSelections[game.id] === game.away_team ? 'selected' : ''} ${game.locked ? 'bg-gray-400 cursor-not-allowed opacity-50' : ''}`}
                      onClick={(e) => {
                        if (game.locked) {
                          e.preventDefault();
                          return;
                        }
                        handleMoneyLineClick(game, game.away_team);
                      }}
                      disabled={game.locked}
                    >
                      {game.away_team}
                    </button>
                    <button
                      className={`team-button ${moneyLineSelections[game.id] === game.home_team ? 'selected' : ''} ${game.locked ? 'bg-gray-400 cursor-not-allowed opacity-50' : ''}`}
                      onClick={(e) => {
                        if (game.locked) {
                          e.preventDefault();
                          return;
                        }
                        handleMoneyLineClick(game, game.home_team);
                      }}
                      disabled={game.locked}
                    >
                      {game.home_team}
                    </button>
                  </div>
                </div>

                {/* Divider Line */}
                {game.prop_bets && game.prop_bets.length > 0 && (
                  <div className="divider-line" />
                )}

                {/* Prop Bet Section */}
                {game.prop_bets && game.prop_bets.length > 0 && (
                  <div className="game-section prop-bet">
                    <p className="prop-question">
                      {game.prop_bets[0].question}{' '}
                      {game.locked && <span className="ml-2 text-gray-500">🔒</span>}
                    </p>
                    <div className="button-row">
                      {game.prop_bets[0].options.map((option, index) => (
                        <button
                          key={index}
                          className={`propbet-button ${propBetSelections[game.prop_bets[0].id] === option ? 'selected' : ''} ${game.locked ? 'bg-gray-400 cursor-not-allowed opacity-50' : ''}`}
                          onClick={(e) => {
                            if (game.locked) {
                              e.preventDefault();
                              return;
                            }
                            handlePropBetClick(game, option);
                          }}
                          disabled={game.locked}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
