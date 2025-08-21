/*
 * Updated Navbar Component 
 * Replaced hamburger menu with ProfileDropdown
 * Maintains all existing functionality and styling
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuthWithNavigation } from "../../hooks/useAuthWithNavigation";
import ProfileDropdown from "../navigation/ProfileDropdown";
import whiteLogo from "../../assets/pickem2_white.png";

export default function Navbar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const { userInfo, logoutAndRedirect } = useAuthWithNavigation();

  const handleLogout = async () => {
    await logoutAndRedirect('/login');
    setIsOpen(false);
  };

  return (
    <nav className="navbar-container">
      <div className="navbar-content">
        <Link to="/">
          <img
            src={whiteLogo}
            alt="Pick Em Logo"
            className="navbar-logo"
          />
        </Link>

        {/* Right side content */}
        <div className="navbar-right">
          {/* Pill-style Auth Buttons for Unauthenticated Users */}
          {!userInfo && location.pathname === "/signup" && (
            <Link
              to="/login"
              className="auth-button login-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="auth-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              <span>Login</span>
            </Link>
          )}

          {!userInfo && location.pathname === "/login" && (
            <Link
              to="/signup"
              className="auth-button signup-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="auth-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Sign Up</span>
            </Link>
          )}

          {/* Desktop Links - Keep existing functionality */}
          {userInfo && (
            <div className="desktop-nav">
              <Link to="/weeks" className="nav-link">Games</Link>
              <Link to="/standings" className="nav-link">Standings</Link>
              <button
                onClick={handleLogout}
                className="logout-button"
              >
                Logout
              </button>
            </div>
          )}

          {/* NEW: Profile Dropdown - Replaces hamburger menu completely */}
          {userInfo && (
            <div className="profile-dropdown-container">
              <ProfileDropdown />
            </div>
          )}
        </div>
      </div>

      {/* 
        REMOVED: Mobile sidebar/hamburger menu 
        ProfileDropdown now handles all mobile navigation
      */}
    </nav>
  );
}