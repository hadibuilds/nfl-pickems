/*
 * Save State Manager Utility - STABLE VERSION
 * Handles save state management and timeout cleanup for game selections
 * FIXED: More stable state management to prevent cleanup spam during rapid clicks
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Custom hook for managing save states and timeouts
 * Provides automatic cleanup to prevent memory leaks
 * @returns {Object} - Save state management functions and data
 */
export const useSaveStateManager = () => {
  const [saveStates, setSaveStates] = useState({});
  const saveTimeoutsRef = useRef({}); // Use ref to avoid dependency issues

  // Cleanup timeouts when component unmounts - but be more stable
  useEffect(() => {
    return () => {
      Object.values(saveTimeoutsRef.current).forEach(timeoutId => {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
      });
      saveTimeoutsRef.current = {}; // Clear the ref
    };
  }, []); // Empty dependency array - only run on mount/unmount

  /**
   * Set save state to 'saving'
   * FIXED: Clears ALL existing save states before showing new spinner
   * @param {string} stateKey - The state key to update
   */
  const setSaving = useCallback((stateKey) => {
    // Clear ALL timeouts (not just current game's timeout)
    Object.values(saveTimeoutsRef.current).forEach(timeoutId => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    });
    
    // Clear ALL save states and timeouts, then set current game to saving
    setSaveStates({ [stateKey]: 'saving' }); // Replace entire state object
    saveTimeoutsRef.current = {}; // Clear all timeouts in ref
  }, []); // No dependencies - function is stable

  /**
   * Set save state to 'saved' with auto-clear timeout
   * @param {string} stateKey - The state key to update
   * @param {number} clearAfter - Milliseconds to auto-clear (default: 2000)
   */
  const setSaved = useCallback((stateKey, clearAfter = 2000) => {
    setSaveStates(prev => ({ ...prev, [stateKey]: 'saved' }));
    
    const timeoutId = setTimeout(() => {
      setSaveStates(prev => {
        const newState = { ...prev };
        delete newState[stateKey];
        return newState;
      });
      delete saveTimeoutsRef.current[stateKey]; // Remove from ref
    }, clearAfter);
    
    saveTimeoutsRef.current[stateKey] = timeoutId; // Store in ref
  }, []);

  /**
   * Set save state to 'error' with auto-clear timeout
   * @param {string} stateKey - The state key to update
   * @param {number} clearAfter - Milliseconds to auto-clear (default: 3000)
   */
  const setError = useCallback((stateKey, clearAfter = 3000) => {
    setSaveStates(prev => ({ ...prev, [stateKey]: 'error' }));
    
    const timeoutId = setTimeout(() => {
      setSaveStates(prev => {
        const newState = { ...prev };
        delete newState[stateKey];
        return newState;
      });
      delete saveTimeoutsRef.current[stateKey]; // Remove from ref
    }, clearAfter);
    
    saveTimeoutsRef.current[stateKey] = timeoutId; // Store in ref
  }, []);

  /**
   * Get current save state for a key
   * @param {string} stateKey - The state key to check
   * @returns {string|null} - 'saving', 'saved', 'error', or null
   */
  const getSaveState = useCallback((stateKey) => {
    return saveStates[stateKey] || null;
  }, [saveStates]);

  /**
   * Generate state key for game actions
   * @param {number} gameId - Game ID
   * @param {string} type - 'moneyline' or 'propbet'
   * @returns {string} - State key
   */
  const generateStateKey = useCallback((gameId, type) => {
    return `${gameId}-${type}`;
  }, []);

  return {
    saveStates,
    setSaving,
    setSaved,
    setError,
    getSaveState,
    generateStateKey,
  };
};