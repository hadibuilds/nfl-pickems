/*
 * Updated Navbar Component
 * 🔒 NAVIGATION PROTECTED: All links use navigateWithConfirmation
 * Prevents navigation away from GamePage with unsaved picks
 * Replaced hamburger menu with ProfileDropdown
 * Maintains all existing functionality and styling
 * ⚡ MEMOIZED: Prevents unnecessary re-renders (logo flicker fix)
 */

import React, { memo } from "react";
import { useLocation } from "react-router-dom";
import { useAuthWithNavigation } from "../../hooks/useAuthWithNavigation";
import ProfileDropdown from "../navigation/ProfileDropdown";
import whiteLogo from "../../assets/pickem2_white.png";

function Navbar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const { userInfo, logoutAndRedirect } = useAuthWithNavigation();

  const handleLogout = async () => {
    await logoutAndRedirect('/login');
    setIsOpen(false);
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
            <div className="profile-dropdown-container">
              <ProfileDropdown />
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

// Export memoized version to prevent re-renders when App state changes
export default memo(Navbar);