// WeekSelector.jsx - Following HomePage pattern with skeleton loading
import React from "react";
import { Link } from "react-router-dom";
import useDashboardData from '../hooks/useDashboardData';
import { useAuth } from '../context/AuthContext';

// Skeleton Component for Week Cards
const WeekCardSkeleton = () => (
  <div className="week-card bg-gradient-to-br from-gray-600 to-gray-700 rounded-2xl shadow-lg animate-pulse">
    <div className="week-card-content">
      <div className="week-card-header">
        <div className="w-20 h-4 bg-gray-500 rounded opacity-70"></div>
        <div className="w-16 h-6 bg-gray-500 rounded opacity-50"></div>
      </div>
      
      <div className="points-container">
        <div className="w-24 h-8 bg-gray-500 rounded mb-1 mx-auto"></div>
      </div>
    </div>
  </div>
);

export default function WeekSelector({ 
  games = [], 
  gameResults = {}, 
  moneyLineSelections = {}, 
  propBetSelections = {}
}) {
  const { userInfo } = useAuth();
  
  // Fetch dashboard data to get currentWeek (following HomePage pattern)
  const { dashboardData, loadingStates, error } = useDashboardData(userInfo, {
    loadGranular: true,
    includeLeaderboard: false, // Don't need leaderboard for weeks page
    sections: ['stats'] // Only need stats section for currentWeek
  });

  const totalWeeks = 18;
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);

  // Extract currentWeek from dashboard data OR use fallback calculation
  const userData = dashboardData?.user_data || {};
  const getCurrentNFLWeekFallback = () => {
    const now = new Date();
    const firstTuesday = new Date('2025-09-02T16:00:00Z');
    const seasonStart = new Date('2025-08-14T00:00:00Z');
    
    if (now >= seasonStart && now < firstTuesday) {
      return 1;
    }
    
    for (let weekNumber = 1; weekNumber <= 18; weekNumber++) {
      const weekStart = new Date(firstTuesday);
      weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7);
      
      if (now >= weekStart && now < weekEnd) {
        return weekNumber;
      }
    }
    
    return null;
  };

  // Use API currentWeek if available, otherwise calculate instantly
  const currentWeek = userData.currentWeek || getCurrentNFLWeekFallback();

  // Not logged in
  if (!userInfo) {
    return (
      <div className="pt-16">
        <h2>you are not logged in</h2>
        <p className="text-center text-small">
          <a href="/login" style={{ color: '#8B5CF6', fontSize: '16px' }}>
            Login
          </a>
        </p>
        <p className="text-center text-small">
          <a href="/signup" style={{ color: '#8B5CF6', fontSize: '16px' }}>
            Sign Up
          </a>
        </p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen pt-16 pb-12 px-6" style={{ backgroundColor: '#1E1E20', color: 'white' }}>
        <div className="page-container">
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-8">
              <p className="text-red-400">Error loading dashboard: {error}</p>
              <button 
                className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                onClick={() => window.location.reload()}
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getCurrentNFLWeek = () => {
    const now = new Date();
    const firstTuesday = new Date('2025-09-02T16:00:00Z');
    const seasonStart = new Date('2025-08-14T00:00:00Z');
    
    if (now >= seasonStart && now < firstTuesday) {
      return 1;
    }
    
    for (let weekNumber = 1; weekNumber <= 18; weekNumber++) {
      const weekStart = new Date(firstTuesday);
      weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7);
      
      if (now >= weekStart && now < weekEnd) {
        return weekNumber;
      }
    }
    
    return null;
  };

  const getWeekStatus = (weekNumber) => {
    const currentNFLWeek = getCurrentNFLWeek();
    const weekGames = games.filter(game => game.week === weekNumber);
    
    if (weekGames.length === 0) {
      if (weekNumber <= currentNFLWeek) {
        return {
          status: 'current',
          points: null,
          label: 'Current'
        };
      } else {
        return {
          status: 'upcoming', 
          points: null,
          label: 'Upcoming'
        };
      }
    }

    const allGamesHaveResults = weekGames.every(game => {
      const hasWinner = gameResults[game.id]?.winner;
      const hasPropResult = !game.prop_bets?.length || 
        game.prop_bets.every(propBet => gameResults[game.id]?.prop_result);
      return hasWinner && hasPropResult;
    });

    if (allGamesHaveResults) {
      let totalPoints = 0;
      weekGames.forEach(game => {
        const userPick = moneyLineSelections[game.id];
        const actualWinner = gameResults[game.id]?.winner;
        if (userPick === actualWinner) {
          totalPoints += 1;
        }

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

    if (weekNumber === currentNFLWeek) {
      return {
        status: 'current',
        points: null,
        label: 'Current'
      };
    }

    if (weekNumber < currentNFLWeek && !allGamesHaveResults) {
      return {
        status: 'current',
        points: null,
        label: 'In Progress'
      };
    }

    return {
      status: 'upcoming',
      points: null,
      label: 'Upcoming'
    };
  };

  const getStatusBadge = (weekNumber, status) => {
    const currentNFLWeek = getCurrentNFLWeek();
    
    if (currentNFLWeek !== null) {
      if (weekNumber === currentNFLWeek) {
        return {
          label: 'Current',
          backgroundColor: '#5B21B6',
          className: 'current-week-badge'
        };
      } else if (weekNumber < currentNFLWeek) {
        return {
          label: status === 'completed' ? 'Completed' : 'In Progress',
          backgroundColor: status === 'completed' ? '#065F46' : '#5B21B6',
          className: status === 'completed' ? 'completed-badge' : 'in-progress-badge'
        };
      } else {
        return {
          label: 'Upcoming',
          backgroundColor: '#374151',
          className: 'upcoming-badge'
        };
      }
    }

    return {
      label: status === 'completed' ? 'Completed' : 
             status === 'current' ? 'Current' : 'Upcoming',
      backgroundColor: status === 'completed' ? '#065F46' : 
                      status === 'current' ? '#5B21B6' : '#374151',
      className: `${status}-badge`
    };
  };

  const getWeekDates = (weekNumber) => {
    const firstTuesday = new Date('2025-09-02T16:00:00Z');
    
    const weekStart = new Date(firstTuesday);
    weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);

    const sameMonth = weekStart.getMonth() === weekEnd.getMonth();
    
    return {
      start: weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      end: sameMonth 
        ? weekEnd.toLocaleDateString('en-US', { day: 'numeric' })
        : weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      sameMonth: sameMonth
    };
  };

  const getCardStyles = (status) => {
    switch (status) {
      case 'completed':
        return {
          backgroundColor: '#10B981',
          borderColor: '#059669',
          textColor: 'white',
          hoverColor: '#047857'
        };
      case 'current':
        return {
          backgroundColor: '#8B5CF6',
          borderColor: '#7C3AED',
          textColor: 'white',
          hoverColor: '#7C3AED'
        };
      case 'upcoming':
        return {
          backgroundColor: '#374151',
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
          <div className="week-selector-wrapper">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {/* Always show week cards immediately - no more skeletons */}
              {weeks.map((week) => {
                const weekStatus = getWeekStatus(week);
                const statusBadge = getStatusBadge(week, weekStatus.status);
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
                        <div className="week-card-header">
                          <div className="week-dates" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                            {weekDates.start} - {weekDates.end}
                          </div>
                          <span 
                            className={`week-status-badge ${statusBadge.className}`}
                            style={{ 
                              backgroundColor: statusBadge.backgroundColor
                            }}
                          >
                            {statusBadge.label}
                          </span>
                        </div>
                     
                        <div className="points-container">
                          {weekStatus.status === 'completed' && weekStatus.points !== null && (
                            <div className="points-earned">
                              <span className="points-label">Points: </span>
                              <span className="points-value">{weekStatus.points}</span>
                            </div>
                          )}
                          <h3 className="week-number">Week {week}</h3>
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
