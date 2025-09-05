import React, { useEffect, useMemo, useRef, useState } from 'react';

export default function UserAvatar({ user, size = 28, currentUsername, borderStyle }) {
  const [open, setOpen] = useState(false);
  const idRef = useRef(`avatar-${Math.random().toString(36).slice(2)}`);

  // ---------- Normalize incoming user fields (snake_case, camelCase, or aliases) ----------
  const norm = useMemo(() => {
    const u = user || {};

    // username fallbacks
    const username =
      u.username ??
      u.userName ??
      (typeof u.email === 'string' ? u.email.split('@')[0] : '') ??
      '';

    // names in either casing
    const firstName = (u.first_name ?? u.firstName ?? '').trim();
    const lastName  = (u.last_name  ?? u.lastName  ?? '').trim();

    // avatar could be in several keys; ignore empty strings
    const rawAvatar =
      u.avatar ??
      u.profilePicture ??
      u.avatar_url ??
      u.avatarUrl ??
      null;
    const avatar = rawAvatar && String(rawAvatar).length > 0 ? String(rawAvatar) : null;

    // optional display name if your API ever sends it
    const displayName =
      (u.display_name ?? u.displayName ?? '').trim() ||
      `${firstName} ${lastName}`.trim() ||
      username;

    // boolean for "this is me"
    const isSelf = u.is_self === true;

    return { username, firstName, lastName, avatar, displayName, isSelf };
  }, [user]);

  // ---------- Helpers ----------
  const getInitials = (firstName, lastName, username) => {
    // 1) First + Last initials
    if (firstName && lastName) {
      return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
    }
    // 2) First two of first name
    if (firstName && firstName.length >= 2) {
      return (firstName.charAt(0) + firstName.charAt(1)).toUpperCase();
    }
    // 3) First letter + 'U'
    if (firstName) {
      return (firstName.charAt(0) + 'U').toUpperCase();
    }
    // 4) Username fallback
    if (username) {
      const names = username.trim().split(/\s+/);
      if (names.length === 1) {
        const n = names[0];
        return (n.charAt(0) + (n.charAt(1) || 'U')).toUpperCase();
      }
      return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
    }
    // 5) Ultimate fallback
    return 'UU';
  };

  const getUserColor = (seed) => {
    const str = String(seed || '');
    let hash = 0;
    for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
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
    if (norm.isSelf) return true;
    if (!resolvedCurrentUsername || !norm.username) return false;
    return String(norm.username).toLowerCase() === String(resolvedCurrentUsername).toLowerCase();
  }, [norm.isSelf, norm.username, resolvedCurrentUsername]);

  const displayName = useMemo(() => {
    if (isYou) return 'You';
    return norm.displayName || norm.username || 'User';
  }, [isYou, norm.displayName, norm.username]);

  const initials = getInitials(norm.firstName, norm.lastName, norm.username);
  const backgroundColor = getUserColor(norm.username);
  const hasAvatar = !!norm.avatar;

  // Border style logic
  const getBorderStyle = () => {
    if (borderStyle === 'peek') {
      return '2px solid #6B7280'; // Gray border for peek cards
    }
    return '2px solid rgba(255,255,255,0.2)'; // Default semi-transparent white
  };

  // Detect touch (no hover)
  const isTouch =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(hover: none) and (pointer: coarse)').matches;

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
          border: getBorderStyle(),
          transition: 'transform 0.2s ease, border-color 0.2s ease',
          transform: open ? 'scale(1.1)' : 'scale(1)',
          borderColor: open ? (borderStyle === 'peek' ? '#9CA3AF' : 'rgba(255,255,255,0.4)') : (borderStyle === 'peek' ? '#6B7280' : 'rgba(255,255,255,0.2)'),
          // Kill focus ring everywhere
          outline: 'none',
          boxShadow: 'none',
          padding: 0,
          lineHeight: 1,
          backgroundImage: hasAvatar ? `url(${norm.avatar})` : 'none',
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
