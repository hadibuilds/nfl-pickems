import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PageLayout from '../components/common/PageLayout';

export default function PeekSelector() {
  const [currentWeek, setCurrentWeek] = useState(null);
  const [availableWeeks, setAvailableWeeks] = useState([]);
  const [games, setGames] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        // Fetch current week
        const res = await fetch(`${API_BASE}/analytics/api/current-week/`, { credentials: 'include' });
        if (!res.ok) throw new Error('failed');
        const data = await res.json();
        const wk = Number(data?.currentWeek ?? 1);
        if (!mounted) return;
        setCurrentWeek(wk);

        const weeks = [];
        for (let i = wk; i >= 1; i--) weeks.push(i);
        setAvailableWeeks(weeks);

        // Fetch all games to count locked games per week
        const gamesRes = await fetch(`${API_BASE}/games/api/games/`, { credentials: 'include' });
        if (gamesRes.ok) {
          const allGames = await gamesRes.json();
          if (mounted) setGames(allGames || []);
        }
      } catch {
        setAvailableWeeks([4, 3, 2, 1]);
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [API_BASE]);

  // Count locked games for a specific week
  const getLockedGamesCount = (weekNumber) => {
    const weekGames = games.filter(game => game.week === weekNumber);
    const now = new Date();
    const lockedGames = weekGames.filter(game => 
      game.locked || new Date(game.start_time) <= now
    );
    return lockedGames.length;
  };

  return (
    <PageLayout backgroundColor="#1E1E20" maxWidth="max-w-6xl">
      {/* Header copy matches your typography; Bebas font is global */}
      <div className="mx-auto mb-6 text-center">
        <h1 className="text-5xl text-white font-bebas">Peek at Picks</h1>
        <p className="mt-1 text-sm" style={{ color: '#9ca3af' }}>
          See how everyone else picked for locked games
        </p>
      </div>

      {isLoading ? (
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {availableWeeks.map((weekNo) => {
            const status =
              currentWeek == null
                ? 'upcoming'
                : weekNo === currentWeek
                ? 'current'
                : weekNo < currentWeek
                ? 'completed'
                : 'upcoming';

            // Custom colors for PeekSelector: light orange for current, gray for past
            const peekColors = {
              current: {
                backgroundColor: '#FB923C', // light orange
                borderColor: '#EA580C',     // darker orange border
                badgeColor: '#9A3412'       // dark orange badge
              },
              completed: {
                backgroundColor: '#374151', // gray (same as upcoming in WeekSelector)
                borderColor: '#4B5563',     // gray border
                badgeColor: '#374151'       // gray badge
              },
              upcoming: {
                backgroundColor: '#374151', // gray
                borderColor: '#4B5563',     // gray border  
                badgeColor: '#374151'       // gray badge
              }
            };

            const colors = peekColors[status];

            return (
              <Link
                key={weekNo}
                to={`/peek/${weekNo}`}              // real week number
                className="week-card"
                style={{
                  backgroundColor: colors.backgroundColor,
                  borderColor: colors.borderColor,
                  color: 'white'
                }}
              >
                <div className="week-card-content">
                  <div className="week-card-header">
                    <div className="week-number">Week {weekNo}</div>
                    <div 
                      className="week-status-badge"
                      style={{
                        backgroundColor: colors.badgeColor,
                        color: 'white'
                      }}
                    >
                      {status === 'current' ? 'Current' : status === 'completed' ? 'Completed' : 'Upcoming'}
                    </div>
                  </div>
                  <div className="week-card-middle">
                    <div className="points-earned">
                      <span className="points-label">Locked games:</span>
                      <span className="points-value">{getLockedGamesCount(weekNo)}</span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
