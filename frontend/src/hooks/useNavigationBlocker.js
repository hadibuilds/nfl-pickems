/*
 * Navigation Blocker Hook
 * Blocks React Router navigation when user has unsaved changes
 * Shows custom modal instead of browser default warning
 */

import { useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export const useNavigationBlocker = (hasUnsavedChanges, onNavigationAttempt) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Block navigation when there are unsaved changes
  useEffect(() => {
    if (!hasUnsavedChanges) return;

    const handlePopState = (event) => {
      // This handles browser back/forward buttons
      event.preventDefault();
      window.history.pushState(null, '', location.pathname + location.search);
      
      // Get the intended destination from browser history
      const intendedPath = event.state?.usr || '/';
      onNavigationAttempt(intendedPath);
    };

    // Add extra history entry to catch back button
    window.history.pushState(null, '', location.pathname + location.search);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [hasUnsavedChanges, location, onNavigationAttempt]);

  // Block programmatic navigation (like clicking navbar links)
  const navigateWithConfirmation = useCallback((path, options = {}) => {
    if (hasUnsavedChanges) {
      // Pass options to the navigation attempt handler
      onNavigationAttempt(path, options);
    } else {
      // No unsaved changes - handle immediately
      if (options.isRefresh && window.refreshAllData) {
        window.refreshAllData();
      } else {
        navigate(path);
      }
    }
  }, [hasUnsavedChanges, navigate, onNavigationAttempt]);

  return { navigateWithConfirmation };
};