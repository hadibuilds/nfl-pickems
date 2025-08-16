/*
 * Save State Indicator Component
 * Displays spinner, checkmark, or error icon based on save state
 */

import React from 'react';

export default function SaveStateIndicator({ saveState }) {
  if (!saveState) return null;

  switch (saveState) {
    case 'saving':
      return (
        <div className="save-spinner">
          <div className="simple-spinner"></div>
        </div>
      );
    case 'saved':
      return (
        <div className="save-success">
          <div className="saved-icon">✓</div>
        </div>
      );
    case 'error':
      return (
        <div className="save-error">
          <div className="error-icon">⚠</div>
        </div>
      );
    default:
      return null;
  }
}