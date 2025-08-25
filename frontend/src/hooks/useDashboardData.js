// hooks/useDashboardData.js — Optimized, robust, and consistent
// - Parallel granular fetches with AbortController
// - Safe immutable merges (no invalid spreads)
// - Fine‑grained loadingStates + single error surface
// - Idempotent reload() and option flags
// - Uses server as source of truth for currentWeek

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Small helper: read Django's CSRF cookie when needed
function getCookie(name) {
  const cookie = document.cookie
    .split('; ')
    .find(row => row.startsWith(name + '='));
  return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
}

/**
 * useDashboardData
 * Fetches granular dashboard data in parallel and merges into a single object.
 *
 * @param {object} userInfo - expects { username } at minimum when authenticated
 * @param {object} options
 *   - includeLeaderboard (boolean): fetch leaderboard block
 *   - loadGranular (boolean): use granular endpoints (stats/accuracy/leaderboard/recent/insights)
 *   - eager (boolean): if true, start fetching even if userInfo is missing (defaults to false)
 */
export default function useDashboardData(
  userInfo,
  { includeLeaderboard = true, loadGranular = true, eager = false } = {}
) {
  const [dashboardData, setDashboardData] = useState(() => ({ user_data: {} }));
  const [loadingStates, setLoadingStates] = useState({
    stats: !!loadGranular,
    accuracy: !!loadGranular,
    leaderboard: !!includeLeaderboard,
    recent: !!loadGranular,
    insights: !!loadGranular,
  });
  const [error, setError] = useState(null);

  // Track latest in-flight request to avoid state updates from stale effects
  const abortRef = useRef(null);

  const updateLoading = useCallback((patch) => {
    setLoadingStates(prev => ({ ...prev, ...patch }));
  }, []);

  const mergeUserData = useCallback((patch) => {
    setDashboardData(prev => ({
      ...prev,
      user_data: { ...(prev?.user_data || {}), ...patch },
    }));
  }, []);

  const mergeRoot = useCallback((patch) => {
    setDashboardData(prev => ({ ...prev, ...patch }));
  }, []);

  const fetchJSON = useCallback(async (path) => {
    const controller = abortRef.current;
    const resp = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
      signal: controller?.signal,
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`${resp.status} ${resp.statusText} for ${path}${text ? ` — ${text}` : ''}`);
    }
    return resp.json();
  }, []);

  const startFetch = useCallback(async () => {
    // Cancel any previous run
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setError(null);

    // Reset loading flags only for enabled sections
    setLoadingStates({
      stats: loadGranular,
      accuracy: loadGranular,
      leaderboard: includeLeaderboard,
      recent: loadGranular,
      insights: loadGranular,
    });

    try {
      if (!loadGranular) {
        // Legacy monolithic endpoint fallback if you still keep it around
        const data = await fetchJSON('/predictions/api/dashboard/realtime/');
        mergeRoot(data || {});
        setLoadingStates({ stats: false, accuracy: false, leaderboard: false, recent: false, insights: false });
        return;
      }

      // Granular parallel fetches
      const tasks = [];

      // STATS — includes currentWeek and basic numbers used on Home
      updateLoading({ stats: true });
      tasks.push(
        fetchJSON('/predictions/api/dashboard/stats/')
          .then((data) => {
            // Normalize expected fields into user_data
            const patch = {
              username: userInfo?.username,
              currentWeek: data.currentWeek,
              weeklyPoints: data.weeklyPoints,
              rank: data.rank,
              totalUsers: data.totalUsers,
              pointsFromLeader: data.pointsFromLeader,
              pendingPicks: data.pendingPicks,
            };
            mergeUserData(patch);
          })
          .catch((e) => { setError((prev) => prev || e.message); })
          .finally(() => updateLoading({ stats: false }))
      );

      // ACCURACY + BEST CATEGORY + TOTAL POINTS
      updateLoading({ accuracy: true });
      tasks.push(
        fetchJSON('/predictions/api/dashboard/accuracy/')
          .then((data) => {
            const patch = {
              overallAccuracy: data.overallAccuracy ?? 0,
              moneylineAccuracy: data.moneylineAccuracy ?? 0,
              propBetAccuracy: data.propBetAccuracy ?? 0,
              bestCategory: data.bestCategory ?? null,
              bestCategoryAccuracy: data.bestCategoryAccuracy ?? 0,
              totalPoints: data.totalPoints ?? 0,
            };
            mergeUserData(patch);
          })
          .catch((e) => { setError((prev) => prev || e.message); })
          .finally(() => updateLoading({ accuracy: false }))
      );

      // LEADERBOARD (optional)
      if (includeLeaderboard) {
        updateLoading({ leaderboard: true });
        tasks.push(
          fetchJSON('/predictions/api/dashboard/leaderboard/')
            .then((data) => {
              // Expecting { leaderboard: [...] }
              mergeRoot({ leaderboard: Array.isArray(data?.leaderboard) ? data.leaderboard : [] });
            })
            .catch((e) => { setError((prev) => prev || e.message); })
            .finally(() => updateLoading({ leaderboard: false }))
        );
      }

      // RECENT GAMES
      updateLoading({ recent: true });
      tasks.push(
        fetchJSON('/predictions/api/dashboard/recent/')
          .then((data) => {
            const patch = { recentGames: Array.isArray(data?.recentGames) ? data.recentGames : [] };
            mergeUserData(patch);
          })
          .catch((e) => { setError((prev) => prev || e.message); })
          .finally(() => updateLoading({ recent: false }))
      );

      // INSIGHTS
      updateLoading({ insights: true });
      tasks.push(
        fetchJSON('/predictions/api/dashboard/insights/')
          .then((data) => {
            mergeRoot({ insights: Array.isArray(data?.insights) ? data.insights : [] });
          })
          .catch((e) => { setError((prev) => prev || e.message); })
          .finally(() => updateLoading({ insights: false }))
      );

      await Promise.all(tasks);
    } catch (e) {
      if (e?.name === 'AbortError') return; // ignore aborted runs
      setError((prev) => prev || e.message);
    }
  }, [includeLeaderboard, loadGranular, userInfo?.username, fetchJSON, mergeRoot, mergeUserData, updateLoading]);

  // Kick off loads when user is available (or eager flag is set)
  useEffect(() => {
    if (!eager && !userInfo?.username) return;
    startFetch();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [eager, userInfo?.username, startFetch]);

  // Stable reload reference for buttons/manual retries
  const reload = useCallback(() => {
    startFetch();
  }, [startFetch]);

  const api = useMemo(() => ({ dashboardData, loadingStates, error, reload }), [dashboardData, loadingStates, error, reload]);
  return api;
}
