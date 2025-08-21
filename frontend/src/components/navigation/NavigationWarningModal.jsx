/*
 * Navigation Warning Modal
 * Shows when user tries to navigate away with unsaved changes
 * Provides Review and Discard options
 */

import React from 'react';
import { createPortal } from 'react-dom';

export default function NavigationWarningModal({ 
  isOpen, 
  draftCount, 
  onReview, 
  onDiscard 
}) {
  if (!isOpen) return null;

  return createPortal(
    <div className="navigation-modal-overlay">
      <div className="navigation-modal">
        <div className="navigation-modal-header">
          <h3>⚠️ Unsaved Changes</h3>
        </div>
        
        <div className="navigation-modal-body">
          <p>
            You have <strong>{draftCount}</strong> unsaved pick{draftCount !== 1 ? 's' : ''}.
          </p>
          <p>
            Review and submit, or discard changes and leave?
          </p>
        </div>
        
        <div className="navigation-modal-footer">
          <button 
            className="navigation-modal-button review"
            onClick={onReview}
          >
            Review
          </button>
          <button 
            className="navigation-modal-button discard"
            onClick={onDiscard}
          >
            Discard
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}