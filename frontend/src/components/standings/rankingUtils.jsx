import React from 'react';

/**
 * Sort standings by points (desc), then username (asc) with week support.
 * Safe on missing fields.
 */
export const sortStandings = (standings = [], selectedWeek = null) => {
  return [...(standings || [])].sort((a, b) => {
    const aPoints = selectedWeek ? (a.weekly_scores?.[selectedWeek] ?? 0) : (a.total_points ?? 0);
    const bPoints = selectedWeek ? (b.weekly_scores?.[selectedWeek] ?? 0) : (b.total_points ?? 0);

    if (bPoints !== aPoints) return bPoints - aPoints; // points desc
    return String(a.username || '').localeCompare(String(b.username || '')); // stable alpha
  });
};

/**
 * Calculate rank with tie handling using consecutive ranking
 * @param {Array} standings - Array of standing objects
 * @param {string} username - Username to calculate rank for
 * @param {number|null} selectedWeek - Week to calculate for (null for total)
 * @returns {string|number} - Rank (e.g., "T-1", 2, 3, etc.)
 */
export const calculateRankWithTies = (standings, username, selectedWeek = null) => {
  if (!Array.isArray(standings) || standings.length === 0) return '—';

  const sorted = sortStandings(standings, selectedWeek);

  const userStanding = sorted.find(
    s => String(s.username || '').toLowerCase() === String(username || '').toLowerCase()
  );
  if (!userStanding) return '—';

  const userPoints = selectedWeek
    ? (userStanding.weekly_scores?.[selectedWeek] ?? 0)
    : (userStanding.total_points ?? 0);

  // consecutive ranking based on unique point tiers
  const uniqueScores = [...new Set(sorted.map(entry =>
    selectedWeek ? (entry.weekly_scores?.[selectedWeek] ?? 0) : (entry.total_points ?? 0)
  ))].sort((a, b) => b - a);

  const actualRank = uniqueScores.findIndex(score => score === userPoints) + 1;

  // show T- prefix if tied at this tier
  const sameTierCount = sorted.filter(e => {
    const pts = selectedWeek ? (e.weekly_scores?.[selectedWeek] ?? 0) : (e.total_points ?? 0);
    return pts === userPoints;
  }).length;

  return sameTierCount > 1 ? `T-${actualRank}` : actualRank;
};

/**
 * Get medal tier for avatar ring colors
 * @returns {number} - Medal tier (1=gold, 2=silver, 3=bronze, 4+=no medal)
 */
export const getMedalTier = (standings, username, selectedWeek = null) => {
  if (!Array.isArray(standings) || standings.length === 0) return 4;

  const userStanding = standings.find(
    s => String(s.username || '').toLowerCase() === String(username || '').toLowerCase()
  );
  if (!userStanding) return 4;

  const userPoints = selectedWeek
    ? (userStanding.weekly_scores?.[selectedWeek] ?? 0)
    : (userStanding.total_points ?? 0);

  const uniqueScores = [...new Set(standings.map(entry =>
    selectedWeek ? (entry.weekly_scores?.[selectedWeek] ?? 0) : (entry.total_points ?? 0)
  ))].sort((a, b) => b - a);

  return uniqueScores.findIndex(score => score === userPoints) + 1;
};

/** Tailwind ring by medal tier */
export const getRingColorClass = (medalTier) => {
  if (medalTier === 1) return 'border-2 border-yellow-400';  // Gold
  if (medalTier === 2) return 'border-2 border-gray-400';    // Silver
  if (medalTier === 3) return 'border-2 border-amber-600';   // Bronze
  return 'border-0';
};

export const capitalizeFirstLetter = (str) => {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// Medal SVG Components
export const GoldMedal = () => (
  <svg width="24" height="24" viewBox="-3.5 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M9.73795 18.8436L12.9511 20.6987L6.42625 32L4.55349 27.8233L9.73795 18.8436Z" fill="#CE4444"/>
    <path d="M9.73795 18.8436L6.52483 16.9885L0 28.2898L4.55349 27.8233L9.73795 18.8436Z" fill="#983535"/>
    <path d="M14.322 18.8436L11.1088 20.6987L17.6337 32L19.5064 27.8233L14.322 18.8436Z" fill="#983535"/>
    <path d="M14.322 18.8436L17.5351 16.9885L24.0599 28.2898L19.5064 27.8233L14.322 18.8436Z" fill="#CE4444"/>
    <path d="M22.9936 11.0622C22.9936 17.1716 18.0409 22.1243 11.9314 22.1243C5.82194 22.1243 0.869249 17.1716 0.869249 11.0622C0.869249 4.9527 5.82194 0 11.9314 0C18.0409 0 22.9936 4.9527 22.9936 11.0622Z" fill="url(#paint0_linear_103_1801)"/>
    <path d="M20.5665 11.0621C20.5665 15.8311 16.7004 19.6972 11.9315 19.6972C7.16247 19.6972 3.29645 15.8311 3.29645 11.0621C3.29645 6.29315 7.16247 2.42713 11.9315 2.42713C16.7004 2.42713 20.5665 6.29315 20.5665 11.0621Z" fill="#A88300"/>
    <path d="M21.0477 11.984C21.0477 16.7641 17.1727 20.6391 12.3926 20.6391C7.61251 20.6391 3.73748 16.7641 3.73748 11.984C3.73748 7.20389 7.61251 3.32887 12.3926 3.32887C17.1727 3.32887 21.0477 7.20389 21.0477 11.984Z" fill="#C28B37"/>
    <path d="M20.5868 11.0621C20.5868 15.8422 16.7118 19.7172 11.9317 19.7172C7.15159 19.7172 3.27656 15.8422 3.27656 11.0621C3.27656 6.28205 7.15159 2.40702 11.9317 2.40702C16.7118 2.40702 20.5868 6.28205 20.5868 11.0621Z" fill="#C09525"/>
    <path d="M11.9781 5.04096L13.8451 8.77502L17.5792 9.24178L15.0151 12.117L15.7122 16.2431L11.9781 14.3761L8.24404 16.2431L8.94729 12.117L6.37701 9.24178L10.1111 8.77502L11.9781 5.04096Z" fill="url(#paint1_linear_103_1801)"/>
    <defs>
      <linearGradient id="paint0_linear_103_1801" x1="11.1804" y1="4.03192" x2="12.6813" y2="31.965" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFC600"/>
        <stop offset="1" stopColor="#FFDE69"/>
      </linearGradient>
      <linearGradient id="paint1_linear_103_1801" x1="11.9783" y1="5.04096" x2="11.9783" y2="16.2431" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFFCDD"/>
        <stop offset="1" stopColor="#FFE896"/>
      </linearGradient>
    </defs>
  </svg>
);

export const SilverMedal = () => (
  <svg width="24" height="24" viewBox="-3.5 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M9.73779 18.8436L12.9509 20.6987L6.42609 32.0001L4.55333 27.8234L9.73779 18.8436Z" fill="#418ED6"/>
    <path d="M9.73779 18.8436L6.52467 16.9885L-0.000155079 28.2899L4.55333 27.8234L9.73779 18.8436Z" fill="#2B63A6"/>
    <path d="M14.3218 18.8436L11.1087 20.6987L17.6335 32.0001L19.5062 27.8234L14.3218 18.8436Z" fill="#2B63A6"/>
    <path d="M14.3218 18.8436L17.5349 16.9885L24.0597 28.2899L19.5062 27.8234L14.3218 18.8436Z" fill="#418ED6"/>
    <circle cx="12.0246" cy="11.0622" r="11.0622" fill="#E3E3E3"/>
    <circle cx="12.0247" cy="11.0621" r="8.63501" fill="#595959"/>
    <mask id="mask0_103_1231" style={{maskType:'alpha'}} maskUnits="userSpaceOnUse" x="3" y="3" width="19" height="18">
      <circle cx="12.4857" cy="11.984" r="8.65511" fill="#C28B37"/>
    </mask>
    <g mask="url(#mask0_103_1231)">
      <circle cx="12.0247" cy="11.0622" r="8.65511" fill="url(#paint0_linear_103_1231)"/>
    </g>
    <path d="M12.0713 5.04102L13.9383 8.77508L17.6724 9.24183L15.1083 12.1171L15.8054 16.2432L12.0713 14.3762L8.33724 16.2432L9.04049 12.1171L6.47021 9.24183L10.2043 8.77508L12.0713 5.04102Z" fill="url(#paint1_linear_103_1231)"/>
    <defs>
      <linearGradient id="paint0_linear_103_1231" x1="12.0247" y1="2.4071" x2="12.0247" y2="19.7173" gradientUnits="userSpaceOnUse">
        <stop stopColor="#9CA1A3"/>
        <stop offset="1" stopColor="#9CA1A3" stopOpacity="0"/>
      </linearGradient>
      <linearGradient id="paint1_linear_103_1231" x1="12.0713" y1="5.04102" x2="12.0713" y2="16.2432" gradientUnits="userSpaceOnUse">
        <stop stopColor="#F1F5F5"/>
        <stop offset="0.0001" stopColor="white"/>
        <stop offset="1" stopColor="#F1F5F5"/>
      </linearGradient>
    </defs>
  </svg>
);

export const BronzeMedal = () => (
  <svg width="24" height="24" viewBox="-3.5 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M9.73779 18.8436L12.9509 20.6987L6.42609 32.0001L4.55333 27.8234L9.73779 18.8436Z" fill="#AA75CB"/>
    <path d="M9.73779 18.8436L6.52467 16.9885L-0.000155079 28.2899L4.55333 27.8234L9.73779 18.8436Z" fill="#73488D"/>
    <path d="M14.3218 18.8436L11.1087 20.6987L17.6335 32.0001L19.5062 27.8234L14.3218 18.8436Z" fill="#73488D"/>
    <path d="M14.3218 18.8436L17.5349 16.9885L24.0597 28.2899L19.5062 27.8234L14.3218 18.8436Z" fill="#AA75CB"/>
    <circle cx="12.0246" cy="11.0622" r="11.0622" fill="#DC9E42"/>
    <circle cx="12.0247" cy="11.0621" r="8.63501" fill="#734C12"/>
    <mask id="mask0_103_1242" style={{maskType:'alpha'}} maskUnits="userSpaceOnUse" x="3" y="3" width="19" height="18">
      <circle cx="12.4857" cy="11.984" r="8.65511" fill="#C28B37"/>
    </mask>
    <g mask="url(#mask0_103_1242)">
      <circle cx="12.0247" cy="11.0622" r="8.65511" fill="#A36D1D"/>
    </g>
    <path d="M12.0713 5.04102L13.9383 8.77508L17.6724 9.24183L15.1083 12.1171L15.8054 16.2432L12.0713 14.3762L8.33724 16.2432L9.04049 12.1171L6.47021 9.24183L10.2043 8.77508L12.0713 5.04102Z" fill="url(#paint0_linear_103_1242)"/>
    <defs>
      <linearGradient id="paint0_linear_103_1242" x1="12.0713" y1="5.04102" x2="12.0713" y2="16.2432" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FCFF80"/>
        <stop offset="0.401042" stopColor="#FDE870"/>
        <stop offset="1" stopColor="#FFC759"/>
      </linearGradient>
    </defs>
  </svg>
);

/** For compatibility; currently always white */
export const getPointColor = () => 'text-white';

/** Medal or numeric rank renderer */
export const renderRank = (medalTier, displayRank) => {
  if (medalTier === 1) return <GoldMedal />;
  if (medalTier === 2) return <SilverMedal />;
  if (medalTier === 3) return <BronzeMedal />;
  return <span className="text-xl font-bold text-white">{displayRank}</span>;
};