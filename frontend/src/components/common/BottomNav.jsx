/*
 * BottomNav - iOS-style bottom navigation for mobile PWA
 * Only shows on mobile devices in PWA/standalone mode
 * Features:
 * - 5 main navigation items
 * - Active state highlighting
 * - Smooth transitions
 * - Safe area padding for iOS notch
 * - Protected navigation (respects unsaved changes)
 * - Tap active icon to scroll to top (Instagram-style)
 */

import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Home, Trophy, Eye, Calendar, User } from 'lucide-react';

const BottomNav = () => {
  const location = useLocation();
  const [currentWeek, setCurrentWeek] = useState(null);
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Fetch current week for Games navigation
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics/api/current-week/`, { credentials: 'include' });
        if (!res.ok) throw new Error('failed');
        const data = await res.json();
        const wk = Number(data?.currentWeek ?? 1);
        if (mounted) setCurrentWeek(wk);
      } catch (e) {
        console.warn('current-week endpoint unavailable; using fallback week 1');
        if (mounted) setCurrentWeek(1);
      }
    })();
    return () => { mounted = false; };
  }, [API_BASE]);

  // Protected navigation handler with scroll-to-top
  const handleNavigate = (path, isCurrentlyActive) => {
    // If tapping active icon, scroll to top
    if (isCurrentlyActive) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Otherwise navigate
    if (window.navigateWithConfirmation) {
      window.navigateWithConfirmation(path);
    } else {
      window.location.href = path;
    }
  };

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: currentWeek ? `/week/${currentWeek}` : '/weeks', icon: Calendar, label: 'Games', matchPattern: '/week' },
    { path: '/standings', icon: Trophy, label: 'Standings' },
    { path: currentWeek ? `/peek/${currentWeek}` : '/peek', icon: Eye, label: 'Peek', matchPattern: '/peek' },
    { path: '/settings', icon: User, label: 'Profile' },
  ];

  // Check if current path matches nav item
  const isActive = (item) => {
    const { path, matchPattern } = item;
    if (path === '/') return location.pathname === '/';
    // For Games, match /week/* routes
    if (matchPattern) return location.pathname.startsWith(matchPattern);
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => {
        const { path, icon: Icon, label } = item;
        const active = isActive(item);
        return (
          <button
            key={label}
            onClick={() => handleNavigate(path, active)}
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
