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

    const scrollY = window.scrollY;
    const body = document.body;

    // Lock scroll
    body.style.position = 'fixed';
    body.style.top = `-${scrollY}px`;
    body.style.left = '0';
    body.style.right = '0';
    body.style.width = '100%';
    body.style.overflow = 'hidden';
    document.documentElement.style.overscrollBehavior = 'contain';

    // Disable pull-to-refresh while modal is open
    body.dataset.modalOpen = 'true';

    return () => {
      // Restore scroll
      body.style.position = '';
      body.style.top = '';
      body.style.left = '';
      body.style.right = '';
      body.style.width = '';
      body.style.overflow = '';
      document.documentElement.style.overscrollBehavior = '';
      delete body.dataset.modalOpen;
      window.scrollTo(0, scrollY);
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