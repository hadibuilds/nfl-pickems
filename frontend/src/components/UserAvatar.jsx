/*
 * UserAvatar Component
 * HeroUI-style circular avatar with initials fallback
 * Generates consistent colors based on username hash
 */

import React from 'react';

export default function UserAvatar({ 
  username, 
  size = 'sm', 
  onClick, 
  className = '',
  profilePicture = null 
}) {
  // Generate initials from username
  const getInitials = (name) => {
    if (!name) return 'U';
    const names = name.trim().split(' ');
    if (names.length === 1) {
      return names[0].charAt(0).toUpperCase();
    }
    return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
  };

  // Generate consistent color from username
  const getAvatarColor = (name) => {
    if (!name) return '#8B5CF6';
    
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    // Generate colors in purple/blue spectrum for consistency
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

  // Size configurations matching HeroUI
  const sizeClasses = {
    sm: 'avatar-sm',
    md: 'avatar-md', 
    lg: 'avatar-lg'
  };

  const avatarColor = getAvatarColor(username);
  const initials = getInitials(username);

  return (
    <button
      className={`user-avatar ${sizeClasses[size]} ${className}`}
      onClick={onClick}
      style={{
        '--avatar-color': avatarColor,
        backgroundImage: profilePicture ? `url(${profilePicture})` : 'none',
        backgroundColor: profilePicture ? 'transparent' : avatarColor,
      }}
      aria-label={`User avatar for ${username}`}
    >
      {!profilePicture && (
        <span className="avatar-initials">
          {initials}
        </span>
      )}
    </button>
  );
}