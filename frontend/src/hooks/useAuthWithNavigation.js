/*
 * Custom Hook for Auth + Navigation
 * Combines useAuth and useNavigate for convenience
 * Provides auth functions that automatically handle navigation
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

  // Login with automatic redirect
  const loginAndRedirect = async (credentials, redirectTo = '/') => {
    const result = await auth.login(credentials);
    
    if (result.success) {
      navigate(redirectTo);
    }
    
    return result;
  };

  // Return all auth functions plus navigation-enhanced versions
  return {
    ...auth,
    logoutAndRedirect,
    loginAndRedirect,
    navigate,
  };
};