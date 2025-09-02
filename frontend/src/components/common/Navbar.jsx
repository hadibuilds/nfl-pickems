/*
 * Updated Navbar Component 
 * 🔒 NAVIGATION PROTECTED: All links use navigateWithConfirmation
 * Prevents navigation away from GamePage with unsaved picks
 * Replaced hamburger menu with ProfileDropdown
 * Maintains all existing functionality and styling
 */

import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuthWithNavigation } from "../../hooks/useAuthWithNavigation";
import ProfileDropdown from "../navigation/ProfileDropdown";
import whiteLogo from "../../assets/pickem2_white.png";

export default function Navbar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const { userInfo, logoutAndRedirect, refreshUser } = useAuthWithNavigation();
  const [isSyncing, setIsSyncing] = useState(false);

  const handleLogout = async () => {
    await logoutAndRedirect('/login');
    setIsOpen(false);
  };

  const handleSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      await refreshUser();
      // Optional: trigger a brief visual feedback
      setTimeout(() => setIsSyncing(false), 500);
    } catch (error) {
      console.error('Sync failed:', error);
      setIsSyncing(false);
    }
  };

  // 🔒 PROTECTED NAVIGATION: Use navigateWithConfirmation if available
  const handleNavigate = (path) => {
    if (window.navigateWithConfirmation) {
      window.navigateWithConfirmation(path);
    } else {
      // Fallback to normal navigation if NavigationManager not active
      window.location.href = path;
    }
  };

  // 🔒 PROTECTED LINK: Custom Link component that respects navigation blocking
  const ProtectedLink = ({ to, children, className, onClick }) => {
    const handleClick = (e) => {
      e.preventDefault();
      if (onClick) onClick();
      handleNavigate(to);
    };

    return (
      <a href={to} className={className} onClick={handleClick}>
        {children}
      </a>
    );
  };

  return (
    <nav className="navbar-container">
      <div className="navbar-content">
        <ProtectedLink to="/">
          <img
            src={whiteLogo}
            alt="Pick Em Logo"
            className="navbar-logo"
          />
        </ProtectedLink>

        {/* Right side content */}
        <div className="navbar-right">
          {/* Pill-style Auth Buttons for Unauthenticated Users */}
          {!userInfo && location.pathname === "/signup" && (
            <ProtectedLink
              to="/login"
              className="auth-button login-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="auth-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              <span>Login</span>
            </ProtectedLink>
          )}

          {!userInfo && location.pathname === "/login" && (
            <ProtectedLink
              to="/signup"
              className="auth-button signup-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="auth-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span>Sign Up</span>
            </ProtectedLink>
          )}
          
          {userInfo && (
            <div className="profile-dropdown-container" style={{ display: 'flex', alignItems: 'center' }}>
              {/* Sync Button */}
              <button
                onClick={handleSync}
                disabled={isSyncing}
                className="sync-button"
                title="Refresh profile data"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: isSyncing ? '#8B5CF6' : '#9CA3AF',
                  cursor: isSyncing ? 'not-allowed' : 'pointer',
                  padding: '8px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'color 0.2s ease',
                  marginRight: '8px',
                }}
                onMouseEnter={(e) => {
                  if (!isSyncing) e.target.style.color = '#D1D5DB';
                }}
                onMouseLeave={(e) => {
                  if (!isSyncing) e.target.style.color = '#9CA3AF';
                }}
              >
                <svg
                  className={isSyncing ? 'animate-spin' : ''}
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                  <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                  <path d="M3 21v-5h5" />
                </svg>
              </button>
              <ProfileDropdown />
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}