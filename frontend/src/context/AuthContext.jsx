/*
 * Authentication Context - Clean Version
 * Only handles auth state, no navigation logic
 * Components handle their own navigation after auth actions
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = import.meta.env.VITE_API_URL;

  // Check if user is already logged in on app start
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // First ensure we have CSRF token
        await fetch(`${API_BASE}/accounts/api/csrf/`, {
          credentials: 'include',
        });

        // Try the whoami endpoint (like your old version)
        const res = await fetch(`${API_BASE}/accounts/api/whoami/`, {
          credentials: 'include',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          },
        });
        
        console.log('Auth check response:', res.status, res.statusText);
        
        if (res.ok) {
          const userData = await res.json();
          console.log('Auth check data:', userData);
          setUserInfo(userData?.username ? userData : null);
        } else {
          console.log('Auth check failed - user not logged in');
          setUserInfo(null);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        setUserInfo(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [API_BASE]);

  // Login function - only handles auth, no navigation
  const login = async (credentials) => {
    try {
      const res = await fetch(`${API_BASE}/accounts/api/login/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(credentials),
      });

      const data = await res.json();
      
      if (res.ok) {
        setUserInfo(data);
        return { success: true, user: data };
      } else {
        return { success: false, error: data.detail || 'Login failed' };
      }
    } catch (err) {
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  // Logout function - only clears auth state, no navigation
  const logout = async () => {
    try {
      await fetch(`${API_BASE}/accounts/api/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Always clear user info, even if API call fails
      setUserInfo(null);
      localStorage.setItem('justLoggedOut', 'true');
    }
  };

  const value = {
    userInfo,
    setUserInfo,
    isLoading,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Helper function for CSRF token
const getCookie = (name) => {
  const cookie = document.cookie
    .split("; ")
    .find(row => row.startsWith(name + "="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
};