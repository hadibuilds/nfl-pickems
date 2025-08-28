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
  propBetSelections = {} 
}) {
  const totalWeeks = 18;
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);

  const [serverCurrentWeek, setServerCurrentWeek] = useState(null);
  const [serverWeeks, setServerWeeks] = useState(null);
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        // prefer analytics, fall back to legacy
        const tryPaths = ['/analytics/api/current-week/', '/predictions/api/current-week/'];
        let data = null, lastErr = null;
        for (const p of tryPaths) {
          try {
            const res = await fetch(`${API_BASE}${p}`, { credentials: 'include' });
            if (!res.ok) continue;
            const ct = (res.headers.get('content-type') || '').toLowerCase();
            if (!ct.includes('application/json')) continue;
            data = await res.json();
            break;
          } catch (e) { lastErr = e; }
        }
        if (!mounted || !data) return;

        if (Number.isInteger(data.currentWeek)) setServerCurrentWeek(data.currentWeek);
        if (Array.isArray(data.weeks)) setServerWeeks(data.weeks);
      } catch (e) {
        console.warn('current-week endpoint unavailable; using fallback week calc');
      }
    })();
    return () => { mounted = false; };
  }, [API_BASE]);

  const getCurrentNFLWeekFallback = () => {
    const now = new Date();
    const firstTuesday = new Date('2025-09-02T16:00:00Z'); // Sept 2, 2025 8 AM PST
    const seasonStart = new Date('2025-08-14T00:00:00Z'); // Week 1 opens early
    
    if (now >= seasonStart && now < firstTuesday) return 1;

    for (let weekNumber = 1; weekNumber <= 18; weekNumber++) {
      const weekStart = new Date(firstTuesday);
      weekStart.setDate(firstTuesday.getDate() + ((weekNumber - 1) * 7));
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7);
      if (now >= weekStart && now < weekEnd) return weekNumber;
    }
    return null;
  };

  const getResolvedCurrentWeek = () => {
    return serverCurrentWeek ?? getCurrentNFLWeekFallback();
  };

  const getWeekStatus = (weekNumber) => {
    const currentNFLWeek = getResolvedCurrentWeek();
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

    if (currentNFLWeek && weekNumber === currentNFLWeek) {
      return { status: 'current', points: null, label: 'Current' };
    }

    if (currentNFLWeek && weekNumber < currentNFLWeek && !allGamesHaveResults) {
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
    <div className="min-h-screen pt-16 pb-12 px-6" style={{ backgroundColor: '#1E1E20', color: 'white' }}>
      <div className="page-container">
        <div className="max-w-6xl mx-auto">
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
                      onMouseEnter={(e) => { e.target.style.backgroundColor = styles.hoverColor; }}
                      onMouseLeave={(e) => { e.target.style.backgroundColor = styles.backgroundColor; }}
                    >
                      <div className="week-card-content">
                        <div className="week-card-header">
                          <div className="week-dates" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                            {weekDates.start} - {weekDates.end}
                          </div>
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
