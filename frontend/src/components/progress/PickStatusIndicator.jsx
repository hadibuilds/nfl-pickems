/*
PickStatusIndicator.jsx
Main status indicator for individual picks showing draft/submitted/edited states
*/

import React from 'react';
import SaveStateIndicator from '../picks/SaveStateIndicator';

function PickStatusIndicator({ 
  gameId, 
  isDraft = false, 
  isSubmitted = false, 
  wasEdited = false,
  saveState = null,
  className = ""
}) {
  // Priority: Save state > Draft/Edit states > Submitted
  if (saveState) {
    return <SaveStateIndicator saveState={saveState} />;
  }

  if (isDraft && wasEdited) {
    return (
      <div className={`status-indicator status-edited ${className}`}>
        <span className="status-icon">⚠</span>
        <span className="status-text">Modified</span>
      </div>
    );
  }

  if (isDraft) {
    return (
      <div className={`status-indicator status-draft ${className}`}>
        <span className="status-icon">📝</span>
        <span className="status-text">Draft</span>
      </div>
    );
  }

  if (isSubmitted) {
    return (
      <div className={`status-indicator status-submitted ${className}`}>
        <span className="status-icon">✓</span>
        <span className="status-text">Submitted</span>
      </div>
    );
  }

  return null;
}

export default PickStatusIndicator;