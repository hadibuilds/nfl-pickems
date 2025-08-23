/*
 * Updated WeekSelector.jsx - CSS-Based Responsive Scaling
 * REMOVED: JavaScript viewport scaling calculations
 * RELIES ON: CSS responsive system with viewport units and clamp()
 * MAINTAINS: All week logic, status, dates, and styling
 */

import React from "react";
import { Link } from "react-router-dom";

export default function WeekSelector({ 
  games = [], 
  gameResults = {}, 
  moneyLineSelections = {}, 
  propBetSelections = {} 
}) {
  const totalWeeks = 18;
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);

  // REMOVED: JavaScript scaling calculations - CSS handles this now

  const getCurrentNFLWeek = () => {
    const now = new Date();
    const firstTuesday = new Date('2025-09-02T16:00:00Z'); // Sept 2, 2025 8 AM PST
    const seasonStart = new Date('2025-08-14T00:00:00Z'); // Week 1 opens early (today)
    
    // EXCEPTION: Week 1 starts early (August 14) but ends on normal schedule
    if (now >= seasonStart && now < firstTuesday) {
      return 1; // Extended Week 1 period
    }
    
    // Normal weekly logic starting from Week 1's official Tuesday
    for (let weekNumber = 1; weekNumber <= 18; weekNumber++) {
      const weekStart = new Date(firstTuesday);
      weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7); // Next Tuesday
      
      // If now is between this Tuesday and next Tuesday, this is the current week
      if (now >= weekStart && now < weekEnd) {
        return weekNumber;
      }
    }
    
    // If we're after Week 18 ends, return null (post-season)
    return null;
  };

  const getWeekStatus = (weekNumber) => {
    const currentNFLWeek = getCurrentNFLWeek();
    const weekGames = games.filter(game => game.week === weekNumber);
    
    // If no games, it's upcoming (shouldn't happen since you populated all weeks)
    if (weekGames.length === 0) {
      return {
        status: 'upcoming',
        points: null,
        label: 'Coming Soon'
      };
    }

    // Check if ALL games have results (winner field populated in database)
    // AND all prop bets have correct_answer populated
    const allGamesHaveResults = weekGames.every(game => {
      // Check if game has winner (from your Game.winner field)
      const hasMoneyLineResult = gameResults[game.id]?.winner;
      
      // Check if all prop bets have correct_answer (from your PropBet.correct_answer field)
      const hasPropResult = !game.prop_bets?.length || 
        game.prop_bets.every(propBet => gameResults[game.id]?.prop_result);
      
      return hasMoneyLineResult && hasPropResult;
    });

    // If all games have results, week is completed
    if (allGamesHaveResults) {
      // Calculate total points earned for this week
      let totalPoints = 0;
      
      weekGames.forEach(game => {
        // Money line points (1pt) - based on Game.winner vs user prediction
        const userMoneyLinePick = moneyLineSelections[game.id];
        const actualWinner = gameResults[game.id]?.winner;
        if (userMoneyLinePick === actualWinner) {
          totalPoints += 1;
        }
        
        // Prop bet points (2pts) - based on PropBet.correct_answer vs user prediction
        if (game.prop_bets?.length > 0) {
          const userPropPick = propBetSelections[game.prop_bets[0].id];
          const actualPropResult = gameResults[game.id]?.prop_result;
          if (userPropPick === actualPropResult) {
            totalPoints += 2;
          }
        }
      });

      return {
        status: 'completed',
        points: totalPoints,
        label: 'Completed'
      };
    }

    // If this is THE current NFL week and not completed, it's current
    if (weekNumber === currentNFLWeek) {
      return {
        status: 'current',
        points: null,
        label: 'Current'
      };
    }

    // If week is before current week but not completed, it's still current
    // (in case games got postponed or results delayed)
    if (weekNumber < currentNFLWeek && !allGamesHaveResults) {
      return {
        status: 'current',
        points: null,
        label: 'In Progress'
      };
    }

    // Otherwise it's upcoming
    return {
      status: 'upcoming',
      points: null,
      label: 'Coming Soon'
    };
  };

  const getWeekDates = (weekNumber) => {
    // Calculate week dates based on Tuesday schedule
    const firstTuesday = new Date('2025-09-02T16:00:00Z'); // Sept 2, 2025 8 AM PST
    
    const weekStart = new Date(firstTuesday);
    weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6); // 7 days later (Tuesday to Monday)
    
    return {
      start: weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      end: weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    };
  };

  const getCardStyles = (status) => {
    switch (status) {
      case 'completed':
        return {
          backgroundColor: '#10B981', // Green
          borderColor: '#059669',
          textColor: 'white',
          hoverColor: '#047857'
        };
      case 'current':
        return {
          backgroundColor: '#8B5CF6', // Purple
          borderColor: '#7C3AED',
          textColor: 'white',
          hoverColor: '#7C3AED'
        };
      case 'upcoming':
        return {
          backgroundColor: '#374151', // Gray
          borderColor: '#4B5563',
          textColor: '#9CA3AF',
          hoverColor: '#4B5563'
        };
      default:
        return {
          backgroundColor: '#2d2d2d',
          borderColor: '#4B5563',
          textColor: 'white',
          hoverColor: '#3a3a3a'
        };
    }
  };

  return (
    <div className="min-h-screen pt-16 pb-12 px-6" style={{ backgroundColor: '#1E1E20', color: 'white' }}>
      <div className="page-container">
        <div className="max-w-6xl mx-auto">
          {/* UPDATED: Removed dynamic scaling - CSS handles responsive scaling */}
          <div className="week-selector-wrapper">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {weeks.map((week) => {
                const weekStatus = getWeekStatus(week);
                const weekDates = getWeekDates(week);
                const styles = getCardStyles(weekStatus.status);

                return (
                  <div key={week} className="week-card-wrapper">
                    <Link
                      to={`/week/${week}`}
                      className="week-card"
                      style={{ 
                        backgroundColor: styles.backgroundColor,
                        borderColor: styles.borderColor,
                        color: styles.textColor
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.backgroundColor = styles.hoverColor;
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.backgroundColor = styles.backgroundColor;
                      }}
                    >
                      <div className="week-card-content">
                        <div className="week-header">
                          <h3 className="week-number">Week {week}</h3>
                          <span 
                            className="week-status-badge" 
                            style={{ 
                              backgroundColor: weekStatus.status === 'completed' ? '#065F46' : 
                                             weekStatus.status === 'current' ? '#5B21B6' : '#374151'
                            }}
                          >
                            {weekStatus.label}
                          </span>
                        </div>
                        
                        <div className="week-dates" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                          {weekDates.start} - {weekDates.end}
                        </div>
                        
                        <div className="week-footer">
                          {weekStatus.status === 'completed' && weekStatus.points !== null && (
                            <div className="points-earned">
                              <span className="points-label">Points: </span>
                              <span className="points-value">{weekStatus.points}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}