import { useState, useEffect } from 'react';
import './App.css';

// Helper function to get CSRF token from cookies
const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

function App() {
  const [userInfo, setUserInfo] = useState(null);
  const [games, setGames] = useState([]);
  const [moneyLineSelections, setMoneyLineSelections] = useState({});
  const [propBetSelections, setPropBetSelections] = useState({});

  useEffect(() => {
    // Fetch logged-in user information (WhoAmI endpoint)
    fetch('http://localhost:8000/accounts/api/whoami/', {
      credentials: 'include',  // Ensure session cookies are sent with requests
    })
      .then(response => response.json())
      .then(data => {
        if (data.username) {
          console.log('Logged in user:', data);  // Log the user info for debugging
          setUserInfo(data);  // Store the logged-in user info in state
        } else {
          console.log('Not logged in');
          setUserInfo(null);  // User is not logged in
        }
      })
      .catch(error => {
        console.error('Error fetching user info:', error);
        setUserInfo(null);
      });

    // Fetch the games from the backend
    fetch('http://localhost:8000/games/api/games/', {
      credentials: 'include',  // Ensure cookies (session) are included
      headers: { Accept: 'application/json' },
    })
      .then(response => response.json())
      .then(data => setGames(data))
      .catch(error => console.error('Error fetching games:', error));

    // Fetch the user's predictions (money-line and prop-bet selections)
    fetch('http://localhost:8000/predictions/api/get-user-predictions/', {
      credentials: 'include',  // Ensure cookies (session) are included
    })
      .then(response => response.json())
      .then(data => {
        const moneyLineSelections = data.predictions.reduce((acc, selection) => {
          acc[selection.game_id] = selection.predicted_winner;
          return acc;
        }, {});

        const propBetSelections = data.prop_bets.reduce((acc, selection) => {
          acc[selection.prop_bet_id] = selection.answer;
          return acc;
        }, {});

        setMoneyLineSelections(moneyLineSelections);
        setPropBetSelections(propBetSelections);
      })
      .catch(error => console.error('Error fetching predictions:', error));
  }, []);

  const handleMoneyLineClick = (gameId, team) => {
    setMoneyLineSelections(prev => {
      const updatedSelections = { ...prev, [gameId]: team };
      fetch('http://localhost:8000/predictions/api/save-selection/', {  // Use correct port
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),  // CSRF token for CSRF protection
        },
        body: JSON.stringify({ game_id: gameId, predicted_winner: team }),
        credentials: 'include',  // Send session cookies (important for authentication)
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            setMoneyLineSelections(updatedSelections);  // Save the updated selections
          } else {
            console.error('Error saving selection:', data.message);
          }
        })
        .catch(error => console.error('Error submitting money-line:', error));

      return updatedSelections;
    });
  };

  const handlePropBetClick = (propBetId, answer) => {
    setPropBetSelections(prev => {
      const updatedSelections = { ...prev, [propBetId]: answer };
      fetch('http://localhost:8000/predictions/api/save-selection/', {  // Use correct port
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),  // CSRF token for CSRF protection
        },
        body: JSON.stringify({ prop_bet_id: propBetId, answer }),
        credentials: 'include',  // Send session cookies (important for authentication)
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            setPropBetSelections(updatedSelections);  // Save the updated selections
          } else {
            console.error('Error saving prop-bet selection:', data.message);
          }
        })
        .catch(error => console.error('Error submitting prop-bet:', error));

      return updatedSelections;
    });
  };

  const sortedGames = [...games].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  return (
    <div className="app-container">
      {userInfo ? (
        <div>
          <h2>Welcome, {userInfo.username}</h2>
          <p>Email: {userInfo.email}</p>
        </div>
      ) : (
        <h2>Not logged in</h2>
      )}

      <h1>Games for Week 1</h1>
      {sortedGames.length === 0 ? (
        <p>Loading...</p>
      ) : (
        sortedGames.map(game => {
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

          const propBet = game.prop_bets?.[0];
          const selectedTeam = moneyLineSelections[game.id];
          const selectedPropAnswer = propBet ? propBetSelections[propBet.id] : null;

          return (
            <div key={game.id} className="game-box">
              {/* Top Half - Money Line */}
              <div className="game-section money-line">
                <div className="game-datetime">
                  <div className="date-line">{dayAndDate}</div>
                  <div className="time-line">{formattedTime}</div>
                </div>
                <p className="matchup">{game.away_team} @ {game.home_team}</p>
                <div className="button-row">
                  <button
                    className={`team-button ${selectedTeam === game.away_team ? 'selected' : ''}`}
                    onClick={() => handleMoneyLineClick(game.id, game.away_team)}
                  >
                    {game.away_team}
                  </button>
                  <button
                    className={`team-button ${selectedTeam === game.home_team ? 'selected' : ''}`}
                    onClick={() => handleMoneyLineClick(game.id, game.home_team)}
                  >
                    {game.home_team}
                  </button>
                </div>
              </div>

              <div className="divider-line" />

              {/* Bottom Half - Prop Bet */}
              {propBet ? (
                <div className="game-section prop-bet">
                  <p className="prop-question">{propBet.question}</p>
                  <div className="button-row">
                    {propBet.options.map((option, index) => (
                      <button
                        key={index}
                        className={`propbet-button ${selectedPropAnswer === option ? 'selected' : ''}`}
                        onClick={() => handlePropBetClick(propBet.id, option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="game-section prop-bet">
                  <p className="prop-question">No prop bet available</p>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

export default App;
