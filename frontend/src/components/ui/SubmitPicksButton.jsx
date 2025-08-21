/*
SubmitPicksButton.jsx
Submit button with confirmation modal showing draft picks for review
*/

import React, { useState } from 'react';

function SubmitPicksButton({ 
  draftCount, 
  onSubmitPicks, 
  isDisabled = false,
  draftMoneylinePicks = {},
  draftPropBetPicks = {},
  games = [],
  className = ""
}) {
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmitClick = () => {
    if (draftCount === 0) return;
    setShowConfirmModal(true);
  };

  const handleConfirmSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSubmitPicks();
      setShowConfirmModal(false);
    } catch (err) {
      console.error("Submit failed:", err);
      alert("Failed to submit picks. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getGameInfo = (gameId) => {
    return games.find(game => game.id.toString() === gameId.toString());
  };

  const getPropBetInfo = (propBetId) => {
    for (const game of games) {
      if (game.prop_bets && game.prop_bets.length > 0) {
        const propBet = game.prop_bets.find(pb => pb.id.toString() === propBetId.toString());
        if (propBet) {
          return { ...propBet, game };
        }
      }
    }
    return null;
  };

  return (
    <>
      <button
        onClick={handleSubmitClick}
        disabled={isDisabled || draftCount === 0}
        className={`submit-picks-button ${draftCount === 0 ? 'disabled' : 'active'} ${className}`}
      >
        {draftCount === 0 ? (
          'No Picks to Submit'
        ) : (
          `Submit ${draftCount} Pick${draftCount !== 1 ? 's' : ''}`
        )}
      </button>

      {showConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowConfirmModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Review Your Picks</h3>
              <button 
                className="modal-close"
                onClick={() => setShowConfirmModal(false)}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-subtitle">
                You're about to submit {draftCount} pick{draftCount !== 1 ? 's' : ''} as final. 
                Once submitted, you can still edit them but they'll become drafts again.
              </p>

              <div className="picks-review">
                {/* Moneyline Picks */}
                {Object.keys(draftMoneylinePicks).length > 0 && (
                  <div className="picks-section">
                    <h4>Game Picks ({Object.keys(draftMoneylinePicks).length})</h4>
                    {Object.entries(draftMoneylinePicks).map(([gameId, team]) => {
                      const game = getGameInfo(gameId);
                      return (
                        <div key={gameId} className="pick-item">
                          <span className="pick-game">
                            {game ? `Week ${game.week}: ${game.away_team} @ ${game.home_team}` : 'Unknown Game'}
                          </span>
                          <span className="pick-selection">{team}</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Prop Bet Picks */}
                {Object.keys(draftPropBetPicks).length > 0 && (
                  <div className="picks-section">
                    <h4>Prop Bets ({Object.keys(draftPropBetPicks).length})</h4>
                    {Object.entries(draftPropBetPicks).map(([propBetId, answer]) => {
                      const propBetInfo = getPropBetInfo(propBetId);
                      return (
                        <div key={propBetId} className="pick-item">
                          <span className="pick-game">
                            {propBetInfo ? 
                              `Week ${propBetInfo.game.week}: ${propBetInfo.question}` : 
                              'Unknown Prop Bet'
                            }
                          </span>
                          <span className="pick-selection">{answer}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer">
              <button 
                className="modal-button secondary"
                onClick={() => setShowConfirmModal(false)}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button 
                className="modal-button primary"
                onClick={handleConfirmSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <span className="spinner"></span>
                    Submitting...
                  </>
                ) : (
                  `Submit ${draftCount} Pick${draftCount !== 1 ? 's' : ''}`
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .submit-picks-button {
          background: #8B5CF6;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s ease;
          min-width: 160px;
        }

        .submit-picks-button.active:hover {
          background: #7C3AED;
          transform: translateY(-1px);
        }

        .submit-picks-button.disabled {
          background: #4B5563;
          cursor: not-allowed;
          opacity: 0.6;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 20px;
        }

        .modal-content {
          background: #2d2d2d;
          border-radius: 12px;
          width: 100%;
          max-width: 500px;
          max-height: 80vh;
          overflow: hidden;
          color: white;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          border-bottom: 1px solid #4B5563;
        }

        .modal-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .modal-close {
          background: none;
          border: none;
          color: #9CA3AF;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .modal-close:hover {
          color: white;
        }

        .modal-body {
          padding: 20px;
          max-height: 400px;
          overflow-y: auto;
        }

        .modal-subtitle {
          color: #D1D5DB;
          margin-bottom: 20px;
          font-size: 14px;
          line-height: 1.5;
        }

        .picks-review {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .picks-section h4 {
          margin: 0 0 12px 0;
          color: #F3F4F6;
          font-size: 16px;
          font-weight: 600;
        }

        .pick-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px;
          background: #1F1F1F;
          border-radius: 8px;
          margin-bottom: 8px;
        }

        .pick-game {
          color: #D1D5DB;
          font-size: 13px;
          flex: 1;
        }

        .pick-selection {
          color: #8B5CF6;
          font-weight: 600;
          font-size: 14px;
          margin-left: 12px;
        }

        .modal-footer {
          display: flex;
          gap: 12px;
          padding: 20px;
          border-top: 1px solid #4B5563;
          justify-content: flex-end;
        }

        .modal-button {
          padding: 10px 20px;
          border-radius: 6px;
          border: none;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .modal-button.secondary {
          background: #4B5563;
          color: white;
        }

        .modal-button.secondary:hover:not(:disabled) {
          background: #6B7280;
        }

        .modal-button.primary {
          background: #8B5CF6;
          color: white;
        }

        .modal-button.primary:hover:not(:disabled) {
          background: #7C3AED;
        }

        .modal-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid transparent;
          border-top: 2px solid white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .modal-content {
            margin: 10px;
          }
          
          .pick-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 4px;
          }
          
          .pick-selection {
            margin-left: 0;
          }
        }
      `}</style>
    </>
  );
}

export default SubmitPicksButton;