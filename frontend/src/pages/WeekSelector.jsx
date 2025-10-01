/*
 * WeekSelector.jsx - Logic-only update to use server current week (with fallback)
 * STYLING UNCHANGED
 */

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function WeekSelector({ 
  games = [], 
  gameResults = {}, 
  moneyLineSelections = {}, 
  propBetSelections = {},
  isAuthLoading = false
}) {
  // Match PeekSelector approach: only show relevant weeks
  const [currentWeek, setCurrentWeek] = useState(null);
  const [availableWeeks, setAvailableWeeks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Match PeekSelector logic exactly
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics/api/current-week/`, { credentials: 'include' });
        if (!res.ok) throw new Error('failed');
        const data = await res.json();
        const wk = Number(data?.currentWeek ?? 1);
        if (!mounted) return;
        setCurrentWeek(wk);

        // Show current week first, then all previous weeks
        const weeks = [];
        for (let i = wk; i >= 1; i--) weeks.push(i);
        setAvailableWeeks(weeks);
      } catch (e) {
        console.warn('current-week endpoint unavailable; using fallback');
        // Fallback: show weeks 1-4 in reverse order
        setAvailableWeeks([4, 3, 2, 1]);
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [API_BASE]);

  // Updated getWeekStatus to use new currentWeek state
  const getWeekStatus = (weekNumber) => {
    const weekGames = games.filter(game => game.week === weekNumber);

    if (weekGames.length === 0) {
      return { status: 'upcoming', points: null, label: 'Coming Soon' };
    }

    const allGamesHaveResults = weekGames.every(game => {
      const hasMoneyLineResult = gameResults[game.id]?.winner;
      const hasPropResult = !game.prop_bets?.length || 
        game.prop_bets.every(() => gameResults[game.id]?.prop_result);
      return hasMoneyLineResult && hasPropResult;
    });

    if (allGamesHaveResults) {
      let totalPoints = 0;
      weekGames.forEach(game => {
        const userMoneyLinePick = moneyLineSelections[game.id];
        const actualWinner = gameResults[game.id]?.winner;
        if (userMoneyLinePick === actualWinner) totalPoints += 1;

        if (game.prop_bets?.length > 0) {
          const userPropPick = propBetSelections[game.prop_bets[0].id];
          const actualPropResult = gameResults[game.id]?.prop_result;
          if (userPropPick === actualPropResult) totalPoints += 2;
        }
      });
      return { status: 'completed', points: totalPoints, label: 'Completed' };
    }

    if (currentWeek && weekNumber === currentWeek) {
      return { status: 'current', points: null, label: 'Current' };
    }

    if (currentWeek && weekNumber < currentWeek && !allGamesHaveResults) {
      return { status: 'current', points: null, label: 'In Progress' };
    }

    return { status: 'upcoming', points: null, label: 'Upcoming' };
  };

  const getWeekDates = (weekNumber) => {
    const firstTuesday = new Date('2025-09-02T16:00:00Z'); // Sept 2, 2025 8 AM PST
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
      sameMonth
    };
  };

  const getCardStyles = (status) => {
    switch (status) {
      case 'completed':
        return { backgroundColor: '#10B981', borderColor: '#059669', textColor: 'white', hoverColor: '#047857' };
      case 'current':
        return { backgroundColor: '#8B5CF6', borderColor: '#7C3AED', textColor: 'white', hoverColor: '#7C3AED' };
      case 'upcoming':
        return { backgroundColor: '#374151', borderColor: '#4B5563', textColor: '#9CA3AF', hoverColor: '#4B5563' };
      default:
        return { backgroundColor: '#2d2d2d', borderColor: '#4B5563', textColor: 'white', hoverColor: '#3a3a3a' };
    }
  };

  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12 px-1 sm:px-4 md:px-6" style={{ backgroundColor: '#1E1E20', color: 'white' }}>
      <div className="page-container">
        <div className="max-w-6xl mx-auto">
          <div className="mx-auto mb-6 text-center">
            <h1 className="text-5xl sm:text-6xl md:text-7xl text-white font-bebas tracking-wider">Pick em!</h1>
            <p className="mt-1 text-base" style={{ color: 'rgb(156, 163, 175)' }}>Select a week to make your picks</p>
          </div>
          <div className="week-selector-wrapper">
            {isLoading && !isAuthLoading ? (
              <div className="text-center text-white py-6">
                <div className="inline-flex items-center">
                  <svg className="animate-spin h-8 w-8 text-violet-500 mr-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
                  </svg>
                  Loading weeks...
                </div>
              </div>
            ) : (
              <div className="grid gap-6 justify-center
                grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {availableWeeks.map((week) => {
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
                      onMouseEnter={(e) => { e.target.style.backgroundColor = styles.hoverColor; }}
                      onMouseLeave={(e) => { e.target.style.backgroundColor = styles.backgroundColor; }}
                    >
                      <div className="week-card-content">
                        <div className="week-card-header">
                          <h3 className="week-number">Week {week}</h3>
                          <div className="week-card-right">
                            <span className="week-status-badge" 
                            style={{ 
                              backgroundColor: weekStatus.status === 'completed' ? '#065F46' : weekStatus.status === 'current' ? '#5B21B6' : '#374151' 
                            }}>{weekStatus.label}</span>
                            <div className="week-dates" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                              {weekDates.start} - {weekDates.end}
                            </div>
                          </div>
                        </div>
                        <div className="points-container">
                          {weekStatus.status === 'completed' && weekStatus.points !== null && (
                            <div className="points-earned">
                              <span className="points-label">Points: </span>
                              <span className="card-value">{weekStatus.points}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </Link>
                  </div>
                );
              })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
