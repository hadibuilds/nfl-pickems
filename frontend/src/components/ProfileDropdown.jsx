/*
 * ProfileDropdown Component
 * HeroUI-style dropdown with avatar trigger
 * Includes profile info, stats, navigation, and logout
 */

import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuthWithNavigation } from '../hooks/useAuthWithNavigation';
import UserAvatar from './UserAvatar';
import UserStatsDisplay from './UserStatsDisplay';

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

  // Handle navigation item clicks
  const handleNavigationClick = () => {
    setIsOpen(false);
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

          {/* Navigation Items */}
          <div className="dropdown-navigation">
            <Link 
              to="/weeks" 
              className="dropdown-item"
              onClick={handleNavigationClick}
            >
              <span className="dropdown-icon">🎮</span>
              Games
            </Link>
            
            <Link 
              to="/standings" 
              className="dropdown-item"
              onClick={handleNavigationClick}
            >
              <span className="dropdown-icon">🏆</span>
              Standings
            </Link>

            <Link 
              to="/settings" 
              className="dropdown-item"
              onClick={handleNavigationClick}
            >
              <span className="dropdown-icon">⚙️</span>
              Settings
            </Link>
          </div>

          {/* Logout Section */}
          <div className="dropdown-logout">
            <button 
              className="dropdown-item danger"
              onClick={handleLogout}
            >
              <span className="dropdown-icon">🚪</span>
              Log Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}