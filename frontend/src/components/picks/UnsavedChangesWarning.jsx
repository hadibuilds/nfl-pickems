/*
UnsavedChangesWarning.jsx
Fixed warning banner that appears when there are unsaved draft picks
*/

import React from 'react';

function UnsavedChangesWarning({ draftCount, onSubmit, onDismiss }) {
  if (draftCount === 0) return null;

  return (
    <>
      <div className="unsaved-warning">
        <div className="warning-content">
          <span className="warning-icon">⚠</span>
          <span className="warning-text">
            You have {draftCount} unsaved pick{draftCount !== 1 ? 's' : ''}
          </span>
          <div className="warning-actions">
            <button className="warning-button submit" onClick={onSubmit}>
              Submit Now
            </button>
            <button className="warning-button dismiss" onClick={onDismiss}>
              ×
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .unsaved-warning {
          position: fixed;
          top: 80px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 900;
          max-width: 400px;
          width: 90%;
        }

        .warning-content {
          background: #F59E0B;
          color: #1F2937;
          padding: 12px 16px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .warning-icon {
          font-size: 16px;
          font-weight: bold;
        }

        .warning-text {
          flex: 1;
          font-size: 14px;
          font-weight: 600;
        }

        .warning-actions {
          display: flex;
          gap: 8px;
        }

        .warning-button {
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .warning-button.submit {
          background: #1F2937;
          color: white;
        }

        .warning-button.submit:hover {
          background: #374151;
        }

        .warning-button.dismiss {
          background: transparent;
          color: #1F2937;
          font-size: 16px;
          padding: 4px 8px;
        }

        .warning-button.dismiss:hover {
          background: rgba(0, 0, 0, 0.1);
        }

        @media (max-width: 768px) {
          .warning-content {
            padding: 10px 12px;
          }
          
          .warning-text {
            font-size: 13px;
          }
        }
      `}</style>
    </>
  );
}

export default UnsavedChangesWarning;