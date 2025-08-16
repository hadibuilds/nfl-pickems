/*
 * Team Logos Utility
 * Maps NFL team abbreviations to logo filenames and provides logo URL generation
 */

const TEAM_LOGOS = {
    'ARI': 'cardinals.png',
    'ATL': 'falcons.png',
    'BAL': 'ravens.png',
    'BUF': 'bills.png',
    'CAR': 'panthers.png',
    'CHI': 'bears.png',
    'CIN': 'bengals.png',
    'CLE': 'browns.png',
    'DAL': 'cowboys.png',
    'DEN': 'broncos.png',
    'DET': 'lions.png',
    'GB': 'packers.png',
    'HOU': 'texans.png',
    'IND': 'colts.png',
    'JAX': 'jaguars.png',
    'KC': 'chiefs.png',
    'LV': 'raiders.png',
    'LAC': 'chargers.png',
    'LAR': 'rams.png',
    'MIA': 'dolphins.png',
    'MIN': 'vikings.png',
    'NE': 'patriots.png',
    'NO': 'saints.png',
    'NYG': 'giants.png',
    'NYJ': 'jets.png',
    'PHI': 'eagles.png',
    'PIT': 'steelers.png',
    'SF': '49ers.png',
    'SEA': 'seahawks.png',
    'TB': 'buccaneers.png',
    'TEN': 'titans.png',
    'WAS': 'commanders.png'
  };
  
  const LOGO_BASE_URL = 'https://raw.githubusercontent.com/hadibuilds/team-logos/master/NFL/';
  
  /**
   * Get team logo URL from GitHub for a given team abbreviation
   * @param {string} teamAbbr - Team abbreviation (e.g., 'KC', 'SF')
   * @returns {string} - Full URL to team logo
   */
  export const getTeamLogo = (teamAbbr) => {
    const logoFile = TEAM_LOGOS[teamAbbr];
    
    if (logoFile) {
      return `${LOGO_BASE_URL}${logoFile}`;
    }
    
    // Fallback: try lowercase
    console.warn(`No logo found for team abbreviation: ${teamAbbr}`);
    return `${LOGO_BASE_URL}${teamAbbr.toLowerCase()}.png`;
  };
  
  /**
   * Check if a team abbreviation has a logo
   * @param {string} teamAbbr - Team abbreviation
   * @returns {boolean} - Whether logo exists
   */
  export const hasTeamLogo = (teamAbbr) => {
    return teamAbbr in TEAM_LOGOS;
  };
  
  /**
   * Get all available team abbreviations
   * @returns {string[]} - Array of team abbreviations
   */
  export const getAllTeamAbbreviations = () => {
    return Object.keys(TEAM_LOGOS);
  };