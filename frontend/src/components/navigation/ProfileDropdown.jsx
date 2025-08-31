/*
 * ProfileDropdown Component
 * 🔒 NAVIGATION PROTECTED: All links use navigateWithConfirmation
 * HeroUI-style dropdown with avatar trigger
 * Includes profile info, stats, navigation, and logout
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuthWithNavigation } from '../../hooks/useAuthWithNavigation';
import UserAvatar from '../common/UserAvatar';
import UserStatsDisplay from '../standings/UserStatsDisplay';

export default function ProfileDropdown() {
  const { userInfo, logoutAndRedirect } = useAuthWithNavigation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  // Handle logout
  const handleLogout = async () => {
    setIsOpen(false);
    await logoutAndRedirect('/login');
  };

  // 🔒 PROTECTED NAVIGATION: Use navigateWithConfirmation if available
  const handleNavigate = (path) => {
    setIsOpen(false);
    if (window.navigateWithConfirmation) {
      window.navigateWithConfirmation(path);
    } else {
      // Fallback to normal navigation if NavigationManager not active
      window.location.href = path;
    }
  };

  // 🔒 PROTECTED LINK: Custom Link component that respects navigation blocking
  const ProtectedDropdownLink = ({ to, children, className }) => {
    const handleClick = (e) => {
      e.preventDefault();
      handleNavigate(to);
    };

    return (
      <a href={to} className={className} onClick={handleClick}>
        {children}
      </a>
    );
  };

  if (!userInfo) {
    return null;
  }

  return (
    <div className="profile-dropdown">
      {/* Avatar Button */}
      <div ref={buttonRef}>
        <UserAvatar
          username={userInfo.username}
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          className={`profile-avatar-trigger ${isOpen ? 'active' : ''}`}
        />
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div ref={dropdownRef} className="profile-dropdown-menu">
          {/* Profile Section */}
          <div className="dropdown-profile">
            <span className="profile-text">Signed in as</span>
            <span className="profile-username">{userInfo.username}</span>
          </div>

          {/* Stats Section */}
          <UserStatsDisplay userInfo={userInfo} />

          {/* Navigation Items - Now Protected */}
          <div className="dropdown-navigation">
            <ProtectedDropdownLink 
              to="/weeks" 
              className="dropdown-item"
            >
              <span className="dropdown-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
                  <line x1="16" x2="16" y1="2" y2="6"/>
                  <line x1="8" x2="8" y1="2" y2="6"/>
                  <line x1="3" x2="21" y1="10" y2="10"/>
                </svg>
              </span>
              Games
            </ProtectedDropdownLink>
            
            <ProtectedDropdownLink 
              to="/standings" 
              className="dropdown-item"
            >
              <span className="dropdown-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
                  <path d="M14 9h1.5a2.5 2.5 0 0 0 0-5H14"/>
                  <path d="M4 22h16"/>
                  <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
                  <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
                  <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
                </svg>
              </span>
              Standings
            </ProtectedDropdownLink>

            <ProtectedDropdownLink 
              to="/peek" 
              className="dropdown-item"
            >
              <span className="dropdown-icon">
                👀
              </span>
              Peek Picks
            </ProtectedDropdownLink>

            <ProtectedDropdownLink 
              to="/settings" 
              className="dropdown-item"
            >
              <span className="dropdown-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M12 1v6m0 6v6"/>
                  <path d="m21 12-6-6-6 6"/>
                </svg>
              </span>
              Settings
            </ProtectedDropdownLink>
            
          </div>

          {/* Logout Section */}
          <div className="dropdown-logout">
            <button 
              className="dropdown-item danger"
              onClick={handleLogout}
            >
              <span className="dropdown-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16,17 21,12 16,7"/>
                  <line x1="21" x2="9" y1="12" y2="12"/>
                </svg>
              </span>
              Log Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}