/*
 * Shared Ranking Utilities
 * Used by both UserStatsDisplay and Standings components
 * Provides consistent ranking logic across the application
 */

/**
 * Calculate rank with tie handling using consecutive ranking
 * @param {Array} standings - Array of standing objects
 * @param {string} username - Username to calculate rank for
 * @param {number|null} selectedWeek - Week to calculate for (null for total)
 * @returns {string|number} - Rank (e.g., "T-1", 2, 3, etc.)
 */
export const calculateRankWithTies = (standings, username, selectedWeek = null) => {
    if (!standings || standings.length === 0) return '—';
    
    // Sort standings by points (descending) then alphabetically
    const sortedStandings = [...standings].sort((a, b) => {
      const aPoints = selectedWeek ? a.weekly_scores?.[selectedWeek] || 0 : a.total_points || 0;
      const bPoints = selectedWeek ? b.weekly_scores?.[selectedWeek] || 0 : b.total_points || 0;
  
      // First sort by points (descending)
      if (bPoints !== aPoints) return bPoints - aPoints;
      
      // If points are tied, sort alphabetically by username
      return a.username.localeCompare(b.username);
    });
  
    // Find user in standings
    const userStanding = sortedStandings.find(standing => 
      standing.username.toLowerCase() === username.toLowerCase()
    );
    
    if (!userStanding) return '—';
  
    const userPoints = selectedWeek 
      ? userStanding.weekly_scores?.[selectedWeek] || 0 
      : userStanding.total_points || 0;
  
    // Get unique scores in descending order for consecutive ranking
    const uniqueScores = [...new Set(sortedStandings.map(entry => 
      selectedWeek ? entry.weekly_scores?.[selectedWeek] || 0 : entry.total_points || 0
    ))].sort((a, b) => b - a);
  
    // Find which unique score tier this player belongs to
    const actualRank = uniqueScores.findIndex(score => score === userPoints) + 1;
  
    // Check if there are ties at this point level
    const playersWithSamePoints = sortedStandings.filter(s => {
      const points = selectedWeek ? s.weekly_scores?.[selectedWeek] || 0 : s.total_points || 0;
      return points === userPoints;
    });
  
    // Display rank with T- prefix if tied
    return playersWithSamePoints.length > 1 ? `T-${actualRank}` : actualRank;
  };
  
  /**
   * Get medal tier for avatar ring colors
   * @param {Array} standings - Array of standing objects  
   * @param {string} username - Username to get medal tier for
   * @param {number|null} selectedWeek - Week to calculate for (null for total)
   * @returns {number} - Medal tier (1=gold, 2=silver, 3=bronze, 4+=no medal)
   */
  export const getMedalTier = (standings, username, selectedWeek = null) => {
    if (!standings || standings.length === 0) return 4;
    
    // Find user in standings
    const userStanding = standings.find(standing => 
      standing.username.toLowerCase() === username.toLowerCase()
    );
    
    if (!userStanding) return 4;
  
    const userPoints = selectedWeek 
      ? userStanding.weekly_scores?.[selectedWeek] || 0 
      : userStanding.total_points || 0;
  
    // Get unique scores in descending order
    const uniqueScores = [...new Set(standings.map(entry => 
      selectedWeek ? entry.weekly_scores?.[selectedWeek] || 0 : entry.total_points || 0
    ))].sort((a, b) => b - a);
  
    // Find which unique score tier this player belongs to
    return uniqueScores.findIndex(score => score === userPoints) + 1;
  };
  
  /**
   * Get ring color class for avatar based on medal tier
   * @param {number} medalTier - Medal tier (1=gold, 2=silver, 3=bronze, 4+=none)
   * @returns {string} - Tailwind CSS classes for ring
   */
  export const getRingColorClass = (medalTier) => {
    if (medalTier === 1) return 'border-2 border-yellow-400';  // Gold
    if (medalTier === 2) return 'border-2 border-gray-400';    // Silver  
    if (medalTier === 3) return 'border-2 border-amber-600';   // Bronze
    return 'border-0'; // No border for 4th place and below
  };

  export const capitalizeFirstLetter = (str) => {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
  };