import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';

import PageLayout from '../components/common/PageLayout';
import WeekHeader from '../components/weeks/WeekHeader';
import PeekGameCard from '../components/peek/PeekGameCard';

export default function PeekPage() {
  const params = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Accept param or state, coerce to Number
  const weekNum = Number(params.weekNumber ?? params.week ?? location.state?.weekNumber);

  const [games, setGames] = useState([]);
  const [peekData, setPeekData] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const getCookie = (name) => {
    const cookie = document.cookie.split('; ').find((row) => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };

  useEffect(() => {
    if (!Number.isFinite(weekNum) || weekNum < 1) {
      setIsLoading(false);
      setError('Invalid week number in URL.');
      return;
    }

    const ac = new AbortController();

    (async () => {
      try {
        setIsLoading(true);
        setError(null);
        setGames([]);
        setPeekData({});

        // 1) Fetch games (server may return the wrong week; we'll enforce client-side)
        const gamesRes = await fetch(
          `${API_BASE}/games/api/games/?week=${encodeURIComponent(weekNum)}`,
          { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') }, signal: ac.signal }
        );
        if (!gamesRes.ok) throw new Error('Failed to fetch games');
        const allGames = await gamesRes.json();

        // 🔒 Enforce week on the client (defensive)
        const strictlyThisWeek = (allGames || []).filter(
          (g) => Number(g.week) === Number(weekNum)
        );

        // Only locked or already-started, then sort
        const now = new Date();
        const lockedGames = strictlyThisWeek
          .filter((g) => g.locked || new Date(g.start_time) <= now)
          .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

        // Helpful debug if server hands us mismatched weeks
        if ((allGames || []).length && strictlyThisWeek.length === 0) {
          console.warn(
            `[PeekPage] No games matched week=${weekNum}. First returned week=`,
            allGames[0]?.week
          );
        }

        // 2) Fetch peek data for same week
        const peekRes = await fetch(
          `${API_BASE}/analytics/api/peek-data/?week=${encodeURIComponent(weekNum)}`,
          { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') }, signal: ac.signal }
        );
        if (!peekRes.ok) throw new Error('Failed to fetch peek data');
        const peekJson = await peekRes.json();

        // 🔒 Filter peek_data to only the games we will render
        const ids = new Set(lockedGames.map((g) => g.id));
        const filteredPeek = {};
        const rawPeek = peekJson?.peek_data || {};
        for (const [gid, val] of Object.entries(rawPeek)) {
          if (ids.has(Number(gid))) filteredPeek[gid] = val;
        }

        setGames(lockedGames);
        setPeekData(filteredPeek);
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Error fetching peek data:', err);
          setError(err.message || 'Failed to load peek data');
        }
      } finally {
        setIsLoading(false);
      }
    })();

    return () => ac.abort();
  }, [weekNum, API_BASE]);

  return (
    <PageLayout backgroundColor="#1E1E20" maxWidth="max-w-4xl">
      <WeekHeader
        weekNumber={Number.isFinite(weekNum) ? weekNum : ''}
        onBack={() => navigate('/peek')}
      />

      {isLoading && (
        <div className="text-center text-white py-6">
          <div className="inline-flex items-center">
            <svg className="animate-spin h-8 w-8 text-violet-500 mr-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
            </svg>
            Loading peek data...
          </div>
        </div>
      )}

      {!isLoading && error && (
        <div className="text-center text-white">
          <h2>Error Loading Peek Data</h2>
          <p>{error}</p>
          <button
            onClick={() => navigate('/peek')}
            style={{ marginTop: 20, padding: '10px 20px', backgroundColor: '#8B5CF6', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Back to Weeks
          </button>
        </div>
      )}

      {!isLoading && !error && games.length === 0 && (
        <div className="text-center text-white">
          <h2>Get outta here peepin&apos; Tom, no games have started yet.</h2>
          <button
            onClick={() => navigate('/peek')}
            style={{ marginTop: 20, padding: '10px 20px', backgroundColor: '#8B5CF6', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Back to Weeks
          </button>
        </div>
      )}

      {!isLoading && !error && games.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto justify-items-center">
          {games.map((game) => (
            <PeekGameCard key={game.id} game={game} peekData={peekData[game.id] || {}} />
          ))}
        </div>
      )}
    </PageLayout>
  );
}
