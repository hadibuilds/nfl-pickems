/*
 * BottomNav - iOS-style bottom navigation for mobile PWA
 * Only shows on mobile devices in PWA/standalone mode
 * Features:
 * - 5 main navigation items
 * - Active state highlighting
 * - Smooth transitions
 * - Safe area padding for iOS notch
 * - Protected navigation (respects unsaved changes)
 */

import React from 'react';
import { useLocation } from 'react-router-dom';
import { Home, Trophy, Eye, Calendar, User } from 'lucide-react';

const BottomNav = () => {
  const location = useLocation();

  // Protected navigation handler
  const handleNavigate = (path) => {
    if (window.navigateWithConfirmation) {
      window.navigateWithConfirmation(path);
    } else {
      window.location.href = path;
    }
  };

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/weeks', icon: Calendar, label: 'Games' },
    { path: '/standings', icon: Trophy, label: 'Standings' },
    { path: '/peek', icon: Eye, label: 'Peek' },
    { path: '/settings', icon: User, label: 'Profile' },
  ];

  // Check if current path matches nav item
  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="bottom-nav">
      {navItems.map(({ path, icon: Icon, label }) => {
        const active = isActive(path);
        return (
          <button
            key={path}
            onClick={() => handleNavigate(path)}
            className={`bottom-nav-item ${active ? 'active' : ''}`}
            aria-label={label}
          >
            <Icon className="bottom-nav-icon" size={24} strokeWidth={active ? 2.5 : 2} />
            <span className="bottom-nav-label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default BottomNav;
