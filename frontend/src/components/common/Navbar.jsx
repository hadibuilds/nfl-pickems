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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
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