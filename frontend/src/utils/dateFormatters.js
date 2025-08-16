/*
 * Date Formatting Utilities
 * Handles game date/time formatting in PST timezone
 */

/**
 * Format game date and time in PST timezone
 * @param {string|Date} startTime - Game start time
 * @returns {Object} - Object with dayAndDate and formattedTime
 */
export const formatGameDateTime = (startTime) => {
    const gameDate = new Date(startTime);
    
    const pstOptions = {
      timeZone: 'America/Los_Angeles',
      weekday: 'short',
      month: '2-digit',
      day: '2-digit',
    };
    
    const timeOptions = {
      timeZone: 'America/Los_Angeles',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    };
    
    const dayAndDate = gameDate.toLocaleDateString('en-US', pstOptions);
    const formattedTime = gameDate.toLocaleTimeString('en-US', timeOptions);
    
    return { dayAndDate, formattedTime };
  };
  
  /**
   * Check if a game is locked based on start time
   * @param {string|Date} startTime - Game start time
   * @param {boolean} manualLock - Manual lock override
   * @returns {boolean} - Whether game is locked
   */
  export const isGameLocked = (startTime, manualLock = false) => {
    return manualLock || new Date(startTime) <= new Date();
  };
  
  /**
   * Format relative time (e.g., "2 hours ago", "in 3 days")
   * @param {string|Date} dateTime - Date to format
   * @returns {string} - Relative time string
   */
  export const formatRelativeTime = (dateTime) => {
    const date = new Date(dateTime);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.round(diffMs / (1000 * 60 * 60));
    
    if (diffHours < -24) {
      return `${Math.abs(Math.round(diffHours / 24))} days ago`;
    } else if (diffHours < -1) {
      return `${Math.abs(diffHours)} hours ago`;
    } else if (diffHours < 0) {
      return 'Recently';
    } else if (diffHours < 1) {
      return 'Soon';
    } else if (diffHours < 24) {
      return `In ${diffHours} hours`;
    } else {
      return `In ${Math.round(diffHours / 24)} days`;
    }
  };