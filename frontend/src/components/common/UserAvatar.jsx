/*
 * UserAvatar Component
 * HeroUI-style circular avatar with initials fallback
 * Generates consistent colors based on username hash
 */

import React from 'react';

export default function UserAvatar({ 
  // existing props
  username, 
  firstName = null,
  lastName = null,
  size = 'sm', 
  onClick, 
  className = '',
  profilePicture = null,

  // added resiliency props (optional, non-breaking)
  first_name = null,
  last_name = null,
  email = null,
  avatar = null,
  avatar_url = null,
  avatarUrl = null,
}) {
  // -------- Normalize inputs (names, username, picture) --------
  const normFirst = (firstName ?? first_name ?? '').trim() || null;
  const normLast  = (lastName  ?? last_name  ?? '').trim() || null;

  // If username not provided, fall back to email prefix (common DRF pattern)
  const normUsername = (username ?? (email ? String(email).split('@')[0] : '')).trim();

  // Accept multiple image keys; keep original profilePicture precedence
  const normPicture = profilePicture ?? avatar ?? avatar_url ?? avatarUrl ?? null;

  // Generate two initials with fallback logic
  const getInitials = (first, last, uname) => {
    if (first && last) return (first.charAt(0) + last.charAt(0)).toUpperCase();
    if (first && first.length >= 2) return (first.charAt(0) + first.charAt(1)).toUpperCase();
    if (first) return (first.charAt(0) + 'U').toUpperCase();

    if (uname) {
      const names = uname.trim().split(' ');
      if (names.length === 1) {
        return names[0].length >= 2
          ? (names[0].charAt(0) + names[0].charAt(1)).toUpperCase()
          : (names[0].charAt(0) + 'U').toUpperCase();
      }
      return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
    }
    return 'UU';
  };

  // Generate consistent color from username
  const getAvatarColor = (name) => {
    if (!name) return '#8B5CF6';
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
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

  // Size configurations matching HeroUI (unchanged)
  const sizeClasses = {
    sm: 'avatar-sm',
    md: 'avatar-md', 
    lg: 'avatar-lg'
  };
  const safeSizeClass = sizeClasses[size] || sizeClasses.sm;

  const avatarColor = getAvatarColor(normUsername);
  const initials = getInitials(normFirst, normLast, normUsername);

  return (
    <button
      className={`user-avatar ${safeSizeClass} ${className}`}
      onClick={onClick}
      style={{
        '--avatar-color': avatarColor,
        backgroundImage: normPicture ? `url(${normPicture})` : 'none',
        backgroundColor: normPicture ? 'transparent' : avatarColor,
      }}
      aria-label={`User avatar for ${normUsername || initials}`}
    >
      {!normPicture && (
        <span className="avatar-initials">
          {initials}
        </span>
      )}
    </button>
  );
}
