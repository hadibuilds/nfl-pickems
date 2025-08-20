/*
 * Updated Navbar Component 
 * Uses useAuthWithNavigation instead of separate hooks
 * Clean logout with proper navigation
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuthWithNavigation } from "../hooks/useAuthWithNavigation";
import whiteLogo from "../assets/pickem2_white.png";

export default function Navbar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const { userInfo, logoutAndRedirect } = useAuthWithNavigation();

  const handleLogout = async () => {
    await logoutAndRedirect('/login'); // This now works properly!
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

          {/* Desktop Links */}
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

          {/* Hamburger menu for mobile */}
          {userInfo && (
            <div className="mobile-menu-toggle">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="hamburger-button"
              >
                <span className={`hamburger-line ${isOpen ? "hamburger-line-1-open" : "hamburger-line-1"}`} />
                <span className={`hamburger-line ${isOpen ? "hamburger-line-2-open" : "hamburger-line-2"}`} />
                <span className={`hamburger-line ${isOpen ? "hamburger-line-3-open" : "hamburger-line-3"}`} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Push Sidebar */}
      <div className={`mobile-sidebar ${isOpen ? "mobile-sidebar-open" : "mobile-sidebar-closed"}`}>
        <div className="mobile-sidebar-content">
          {userInfo && (
            <Link to="/weeks" onClick={() => setIsOpen(false)} className="mobile-nav-link">Games</Link>
          )}
          {userInfo && (
            <Link to="/standings" onClick={() => setIsOpen(false)} className="mobile-nav-link">Standings</Link>
          )}
          {!userInfo && location.pathname !== "/login" && (
            <Link to="/login" onClick={() => setIsOpen(false)} className="mobile-nav-link">Login</Link>
          )}
          {!userInfo && location.pathname !== "/signup" && (
            <Link to="/signup" onClick={() => setIsOpen(false)} className="mobile-nav-link">Sign Up</Link>
          )}
          {userInfo && (
            <button onClick={handleLogout} className="mobile-logout-button">Logout</button>
          )}
        </div>
      </div>
    </nav>
  );
}