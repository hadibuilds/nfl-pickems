/*
 * Custom Hook for Auth + Navigation - Enhanced Version
 * Combines useAuth and useNavigate for convenience
 * Provides auth functions that automatically handle navigation
 * Now includes double-click protection and loading states
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export const useAuthWithNavigation = () => {
  const auth = useAuth();
  const navigate = useNavigate();

  // Logout with automatic redirect
  const logoutAndRedirect = async (redirectTo = '/login') => {
    await auth.logout();
    navigate(redirectTo);
  };

  // Login with automatic redirect - now with protection and refresh
  const loginAndRedirect = async (credentials, redirectTo = '/') => {
    // ✅ PROTECTION: Don't allow login if already in progress
    if (auth.isLoggingIn) {
      return { success: false, error: 'Login already in progress' };
    }

    const result = await auth.login(credentials);
    
    if (result.success) {
      // Don't navigate yet - keep showing login spinner
      // After a brief delay, force a full page refresh to the target URL
      setTimeout(() => {
        window.location.href = redirectTo;
      }, 500); // Short delay for user feedback
    }
    
    return result;
  };

  // Return all auth functions plus navigation-enhanced versions
  return {
    ...auth, // This now includes isLoggingIn from enhanced AuthContext
    logoutAndRedirect,
    loginAndRedirect,
    navigate,
  };
};