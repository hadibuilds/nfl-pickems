/*
 * Navigation Manager Component
 * Manages navigation blocking when user has unsaved changes
 * Lives inside Router context to safely use useNavigate/useLocation
 * Prevents memory leaks by forcing user decision: Submit or Discard
 * Works with existing draft system (draftPicks, draftPropBets)
 */

import React, { useState, useEffect } from 'react';
import { useNavigationBlocker } from '../../hooks/useNavigationBlocker';
import NavigationWarningModal from './NavigationWarningModal';

export default function NavigationManager({ 
  hasUnsavedChanges, 
  draftCount, 
  onClearDrafts 
}) {
  const [showModal, setShowModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(null);

  // Handle navigation attempts when user has unsaved changes
  const handleNavigationAttempt = (intendedPath) => {
    if (hasUnsavedChanges) {
      setPendingNavigation(intendedPath);
      setShowModal(true);
    }
  };

  // Get the navigation function that checks for unsaved changes
  const { navigateWithConfirmation } = useNavigationBlocker(
    hasUnsavedChanges, 
    handleNavigationAttempt
  );

  // Handle browser refresh/close warning (already exists in App.jsx, but adding here for completeness)
  useEffect(() => {
    if (!hasUnsavedChanges) return;

    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = 'You have unsaved picks. Are you sure you want to leave?';
      return event.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);

  // Modal handlers
  const handleReview = () => {
    setShowModal(false);
    setPendingNavigation(null);
    // User stays on page to review picks - no navigation
  };

  const handleDiscard = () => {
    // Clear all draft picks (prevents memory leaks)
    onClearDrafts();
    
    setShowModal(false);
    
    // Now navigate to intended destination
    if (pendingNavigation) {
      // Use setTimeout to ensure state cleanup happens first
      setTimeout(() => {
        window.location.href = pendingNavigation;
      }, 0);
    }
    
    setPendingNavigation(null);
  };

  // Expose navigateWithConfirmation to parent components via window
  // This allows components to use it without prop drilling
  useEffect(() => {
    window.navigateWithConfirmation = navigateWithConfirmation;
    
    return () => {
      delete window.navigateWithConfirmation;
    };
  }, [navigateWithConfirmation]);

  return (
    <NavigationWarningModal
      isOpen={showModal}
      draftCount={draftCount}
      onReview={handleReview}
      onDiscard={handleDiscard}
    />
  );
}