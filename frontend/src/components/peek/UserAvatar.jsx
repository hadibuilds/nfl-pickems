import React, { useEffect, useMemo, useRef, useState } from 'react';

export default function UserAvatar({ user, size = 28, currentUsername }) {
  const [open, setOpen] = useState(false);
  const idRef = useRef(`avatar-${Math.random().toString(36).slice(2)}`);

  // ---------- Helpers ----------
  const getInitials = (firstName, lastName, username) => {
    // Priority 1: First + Last name initials
    if (firstName && lastName) {
      return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
    }
    
    // Priority 2: First initial + second letter of first name
    if (firstName && firstName.length >= 2) {
      return (firstName.charAt(0) + firstName.charAt(1)).toUpperCase();
    }
    
    // Priority 3: First letter of first name + 'U' if only one character
    if (firstName) {
      return (firstName.charAt(0) + 'U').toUpperCase();
    }
    
    // Priority 4: Username fallback
    if (username) {
      const names = username.trim().split(' ');
      if (names.length === 1) {
        return names[0].length >= 2 ? 
          (names[0].charAt(0) + names[0].charAt(1)).toUpperCase() : 
          (names[0].charAt(0) + 'U').toUpperCase();
      }
      return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
    }
    
    return 'UU';
  };

  const getUserColor = (u) => {
    const str = String(u || '');
    let hash = 0;
    for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
    
    // Use the same colorful color wheel as the original
    const colors = [
      '#8B5CF6', // purple-500
      '#7C3AED', // violet-600  
      '#6366F1', // indigo-500
      '#3B82F6', // blue-500
      '#0EA5E9', // sky-500
      '#06B6D4', // cyan-500
      '#10B981', // emerald-500
      '#F59E0B', // amber-500
    ];
    
    return colors[Math.abs(hash) % colors.length];
  };

  const resolvedCurrentUsername = useMemo(() => {
    if (currentUsername) return currentUsername;
    if (typeof window !== 'undefined') {
      if (window.CURRENT_USER?.username) return window.CURRENT_USER.username;
      if (document?.body?.dataset?.username) return document.body.dataset.username;
      try {
        const ls = localStorage.getItem('username');
        if (ls) return ls;
      } catch {}
      const cookie = document.cookie?.split('; ')?.find((row) => row.startsWith('username='));
      if (cookie) return decodeURIComponent(cookie.split('=')[1]);
    }
    return null;
  }, [currentUsername]);

  const isYou = useMemo(() => {
    if (user?.is_self === true) return true;
    if (!resolvedCurrentUsername || !user?.username) return false;
    return String(user.username).toLowerCase() === String(resolvedCurrentUsername).toLowerCase();
  }, [user, resolvedCurrentUsername]);

  const displayName = useMemo(() => {
    if (isYou) return 'You';
    const first = (user?.first_name || '').trim();
    const last = (user?.last_name || '').trim();
    if (first || last) return `${first} ${last}`.trim();
    return user?.username || '';
  }, [isYou, user]);

  const initials = getInitials(user?.first_name, user?.last_name, user?.username);
  const backgroundColor = getUserColor(user?.username);
  const hasAvatar = user?.avatar;

  // Detect touch (no hover)
  const isTouch = typeof window !== 'undefined'
    && window.matchMedia
    && window.matchMedia('(hover: none) and (pointer: coarse)').matches;

  // ---------- Single-open bus ----------
  useEffect(() => {
    const handler = (e) => {
      if (e.detail?.id !== idRef.current) setOpen(false);
    };
    window.addEventListener('avatar-tooltip-open', handler);
    return () => window.removeEventListener('avatar-tooltip-open', handler);
  }, []);

  const announceOpen = () => {
    window.dispatchEvent(new CustomEvent('avatar-tooltip-open', { detail: { id: idRef.current } }));
  };

  const openTooltip = () => {
    announceOpen();
    setOpen(true);
  };
  const closeTooltip = () => setOpen(false);
  const toggleTooltip = () => {
    if (open) {
      setOpen(false);
    } else {
      announceOpen();
      setOpen(true);
    }
  };

  // Auto-hide after 2s on touch so it doesn’t get “stuck”
  useEffect(() => {
    if (!isTouch || !open) return;
    const t = setTimeout(() => setOpen(false), 2000);
    return () => clearTimeout(t);
  }, [open, isTouch]);

  // ---------- Render ----------
  return (
    <div
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={!isTouch ? openTooltip : undefined}
      onMouseLeave={!isTouch ? closeTooltip : undefined}
    >
      {/* Use a button for a11y but nuke focus ring & default focus */}
      <button
        type="button"
        aria-label={displayName || 'avatar'}
        onClick={isTouch ? toggleTooltip : undefined}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTooltip();
          }
        }}
        onMouseDown={(e) => {
          // Prevent default focus to avoid any focus ring flash
          e.preventDefault();
        }}
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          backgroundColor: hasAvatar ? 'transparent' : backgroundColor,
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: `${size * 0.4}px`,
          fontWeight: 'bold',
          cursor: 'pointer',
          border: '2px solid rgba(255,255,255,0.2)',
          transition: 'transform 0.2s ease, border-color 0.2s ease',
          transform: open ? 'scale(1.1)' : 'scale(1)',
          borderColor: open ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.2)',
          // Kill focus ring everywhere
          outline: 'none',
          boxShadow: 'none',
          padding: 0,
          lineHeight: 1,
          backgroundImage: hasAvatar ? `url(${user.avatar})` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        {!hasAvatar && initials}
      </button>

      {/* Tooltip */}
      {open && !!displayName && (
        <div
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: `${size + 5}px`,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(0,0,0,0.9)',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            whiteSpace: 'nowrap',
            zIndex: 10,
            pointerEvents: 'none',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          {displayName}
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              border: '4px solid transparent',
              borderTopColor: 'rgba(0,0,0,0.9)',
            }}
          />
        </div>
      )}
    </div>
  );
}
