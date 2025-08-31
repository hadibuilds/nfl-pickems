import React, { useEffect, useMemo, useRef, useState } from 'react';

export default function UserAvatar({ user, size = 28, currentUsername }) {
  const [open, setOpen] = useState(false);
  const idRef = useRef(`avatar-${Math.random().toString(36).slice(2)}`);

  // ---------- Helpers ----------
  const getInitials = (u) =>
    (u || '')
      .split(/[\s_-]+/)
      .map((p) => p.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);

  const getUserColor = (u) => {
    const str = String(u || '');
    let hash = 0;
    for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 65%, 55%)`;
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

  const initials = getInitials(user?.username);
  const backgroundColor = getUserColor(user?.username);

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
          backgroundColor,
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
        }}
      >
        {initials}
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
