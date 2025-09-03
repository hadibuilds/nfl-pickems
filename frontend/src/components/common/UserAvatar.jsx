import React, { useEffect, useMemo, useRef, useState } from 'react';

export default function UserAvatar({ 
  user, 
  size = 28, 
  currentUsername,
  // Backward compatibility with original API
  username,
  profilePicture,
  onClick,
  className = ''
}) {
  const [open, setOpen] = useState(false);
  const idRef = useRef(`avatar-${Math.random().toString(36).slice(2)}`);

  // Normalize user data to support both new and legacy API
  const normalizedUser = useMemo(() => {
    // If user object is provided, use it directly
    if (user) return user;
    
    // Otherwise, construct user object from legacy props
    return {
      username: username,
      first_name: null, // Legacy API doesn't have first_name
      last_name: null,
      avatar: profilePicture
    };
  }, [user, username, profilePicture]);

  // ---------- Helpers ----------
  // Generate initials with specific priority: First+Last, First+Second letter, Username
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
    
    // Use curated brand colors for consistency
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
    if (normalizedUser?.is_self === true) return true;
    if (!resolvedCurrentUsername || !normalizedUser?.username) return false;
    return String(normalizedUser.username).toLowerCase() === String(resolvedCurrentUsername).toLowerCase();
  }, [normalizedUser, resolvedCurrentUsername]);

  const displayName = useMemo(() => {
    if (isYou) return 'You';
    const first = (normalizedUser?.first_name || '').trim();
    const last = (normalizedUser?.last_name || '').trim();
    if (first || last) return `${first} ${last}`.trim();
    return normalizedUser?.username || '';
  }, [isYou, normalizedUser]);

  // Generate initials using the priority system
  const initials = getInitials(
    normalizedUser?.first_name,
    normalizedUser?.last_name, 
    normalizedUser?.username
  );
  const backgroundColor = getUserColor(normalizedUser?.username);
  const hasAvatar = normalizedUser?.avatar;

  // Handle legacy size format (sm/md/lg)
  const pixelSize = useMemo(() => {
    if (typeof size === 'number') return size;
    const sizeMap = { sm: 32, md: 40, lg: 48 };
    return sizeMap[size] || 32;
  }, [size]);

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
        onClick={onClick || (isTouch ? toggleTooltip : undefined)}
        className={className}
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
          width: `${pixelSize}px`,
          height: `${pixelSize}px`,
          borderRadius: '50%',
          backgroundColor: hasAvatar ? 'transparent' : backgroundColor,
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: `${pixelSize * 0.4}px`,
          fontWeight: 'bold',
          cursor: 'pointer',
          border: '2px solid rgba(255,255,255,0.2)',
          transition: 'transform 0.2s ease, border-color 0.2s ease',
          transform: open ? 'scale(1.05)' : 'scale(1)',
          borderColor: open ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.2)',
          // Kill focus ring everywhere
          outline: 'none',
          boxShadow: 'none',
          padding: 0,
          lineHeight: 1,
          backgroundImage: hasAvatar ? `url(${normalizedUser.avatar})` : 'none',
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
            bottom: `${pixelSize + 5}px`,
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
