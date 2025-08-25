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

  // Login with automatic redirect - now with protection
  const loginAndRedirect = async (credentials, redirectTo = '/') => {
    // ✅ PROTECTION: Don't allow login if already in progress
    if (auth.isLoggingIn) {
      console.log('Login already in progress, ignoring duplicate loginAndRedirect call');
      return { success: false, error: 'Login already in progress' };
    }

    const result = await auth.login(credentials);
    
    if (result.success) {
      navigate(redirectTo);
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