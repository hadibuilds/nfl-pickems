/*
SaveStateIndicator.jsx
Shows spinner, success, or error states for individual pick saves
*/

import React from 'react';

function SaveStateIndicator({ saveState, className = "" }) {
  switch (saveState) {
    case 'saving':
      return (
        <div className={`save-indicator save-saving ${className}`}>
          <div className="save-spinner"></div>
        </div>
      );
    
    case 'saved':
      return (
        <div className={`save-indicator save-success ${className}`}>
          <div className="save-icon">✓</div>
        </div>
      );
    
    case 'error':
      return (
        <div className={`save-indicator save-error ${className}`}>
          <div className="save-icon">⚠</div>
        </div>
      );
    
    default:
      return null;
  }
}

export default SaveStateIndicator;