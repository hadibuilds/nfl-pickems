/*
 * Navigation Warning Modal
 * Shows when user tries to navigate away with unsaved changes
 * Provides Review and Discard options
 */

import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

export default function NavigationWarningModal({
  isOpen,
  draftCount,
  onReview,
  onDiscard
}) {
  // Lock scroll when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const body = document.body;
    const html = document.documentElement;

    // Lock scroll without changing position
    const originalOverflow = body.style.overflow;
    const originalHtmlOverflow = html.style.overflow;

    body.style.overflow = 'hidden';
    html.style.overflow = 'hidden';
    html.style.overscrollBehavior = 'contain';

    // Disable pull-to-refresh while modal is open
    body.dataset.modalOpen = 'true';

    return () => {
      // Restore scroll
      body.style.overflow = originalOverflow;
      html.style.overflow = originalHtmlOverflow;
      html.style.overscrollBehavior = '';
      delete body.dataset.modalOpen;
    };
  }, [isOpen]);

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
            onMouseDown={(e) => {
              e.preventDefault();
              onReview();
            }}
          >
            Review
          </button>
          <button
            className="navigation-modal-button discard"
            onMouseDown={(e) => {
              e.preventDefault();
              onDiscard();
            }}
          >
            Discard & Leave
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}