/*
PicksProgressIndicator.jsx
Progress bar showing overall completion with draft/submitted breakdown
*/

import React from 'react';

function PicksProgressIndicator({ 
  totalGames = 0,
  draftCount = 0,
  submittedCount = 0,
  showPoints = false,
  points = 0,
  maxPoints = 0
}) {
  const totalPicks = draftCount + submittedCount;
  const progressPercentage = totalGames > 0 ? (totalPicks / totalGames) * 100 : 0;

  if (totalGames === 0) return null;

  return (
    <>
      <div className="progress-indicator">
        <div className="progress-header">
          <span className="progress-text">
            Picks made: {totalPicks}/{totalGames}
          </span>
          {draftCount > 0 && (
            <span className="draft-warning">
              ({draftCount} unsaved)
            </span>
          )}
        </div>
        
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${progressPercentage}%` }}
          ></div>
          {draftCount > 0 && (
            <div 
              className="progress-draft-overlay"
              style={{ 
                width: `${totalGames > 0 ? (draftCount / totalGames) * 100 : 0}%`,
                left: `${totalGames > 0 ? (submittedCount / totalGames) * 100 : 0}%`
              }}
            ></div>
          )}
        </div>

        {showPoints && points > 0 && (
          <div className="points-display">
            Points: {points}/{maxPoints}
          </div>
        )}
      </div>

      <style jsx>{`
        .progress-indicator {
          background: #2d2d2d;
          padding: 16px;
          border-radius: 8px;
          margin: 16px 0;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .progress-text {
          color: #D1D5DB;
          font-size: 14px;
          font-weight: 500;
        }

        .draft-warning {
          color: #F59E0B;
          font-size: 12px;
          font-weight: 600;
        }

        .progress-bar {
          position: relative;
          width: 100%;
          height: 8px;
          background: #4B5563;
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: #10B981;
          transition: width 0.3s ease;
        }

        .progress-draft-overlay {
          position: absolute;
          top: 0;
          height: 100%;
          background: #F59E0B;
          transition: all 0.3s ease;
        }

        .points-display {
          margin-top: 8px;
          text-align: center;
          color: #10B981;
          font-size: 14px;
          font-weight: 600;
        }
      `}</style>
    </>
  );
}

export default PicksProgressIndicator;