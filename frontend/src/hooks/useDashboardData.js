// hooks/useDashboardData.js — wired to analytics/* endpoints
// - Parallel granular fetches with AbortController
// - Safe immutable merges (no invalid spreads)
// - Fine-grained loadingStates + single error surface
// - Idempotent reload() and option flags
// - Uses server as source of truth for currentWeek and leaderboard anchor window

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
        // If you still keep a legacy monolith endpoint around, surface it here
        const data = await fetchJSON('/analytics/api/dashboard/');
        mergeRoot(data || {});
        setLoadingStates({ stats: false, accuracy: false, leaderboard: false, recent: false, insights: false });
        return;
      }

      // --- 1) STATS (anchor for leaderboard + week header tile) ---
      updateLoading({ stats: true });
      const statsPromise = fetchJSON('/analytics/api/stats-summary/')
        .then((stats) => {
          // Normalize expected fields into user_data
          const patch = {
            username: userInfo?.username,
            currentWeek: stats.currentWeek ?? null,
            weeklyPoints: stats.weeklyPoints ?? 0,
            rank: stats.rank ?? null,
            pointsFromLeader: stats.pointsFromLeader ?? 0,
            // keep a copy of anchor window for downstream calls
            _anchorWindowKey: stats?.window?.key || null,
          };
          mergeUserData(patch);
        })
        .catch((e) => { setError((prev) => prev || e.message); })
        .finally(() => updateLoading({ stats: false }));

      // --- 2) ACCURACY (season rings + best category + total points) ---
      updateLoading({ accuracy: true });
      const accuracyPromise = fetchJSON('/analytics/api/accuracy-summary/')
        .then((a) => {
          const patch = {
            overallAccuracy: a.overallAccuracy ?? 0,           // 0..1 for rings
            moneylineAccuracy: a.moneylineAccuracy ?? 0,       // 0..1
            propBetAccuracy: a.propBetAccuracy ?? 0,           // 0..1
            bestCategory: a.bestCategory ?? null,              // if you added this server-side
            bestCategoryAccuracy: a.bestCategoryAccuracy ?? 0, // %
            totalPoints: a.totalPoints ?? 0,
          };
          mergeUserData(patch);
        })
        .catch((e) => { setError((prev) => prev || e.message); })
        .finally(() => updateLoading({ accuracy: false }));

      // Wait for stats to know the anchor window for leaderboard
      const [statsResult, accuracyResult] = await Promise.all([statsPromise, accuracyPromise]);

      // Get the anchor window key from the stats response directly
      let windowKey = null;
      try {
        const statsData = await fetchJSON('/analytics/api/stats-summary/');
        windowKey = statsData?.window?.key || null;
      } catch (e) {
        // If we can't get window key, leaderboard will be skipped
        windowKey = null;
      }

      const tasks = [];

      // --- 3) LEADERBOARD (optional; needs window_key) ---
      if (includeLeaderboard && windowKey) {
        updateLoading({ leaderboard: true });
        tasks.push(
          fetchJSON(`/analytics/api/leaderboard/?window_key=${encodeURIComponent(windowKey)}&limit=10`)
            .then((data) => {
              mergeRoot({ leaderboard: Array.isArray(data?.leaderboard) ? data.leaderboard : [] });
            })
            .catch((e) => { setError((prev) => prev || e.message); })
            .finally(() => updateLoading({ leaderboard: false }))
        );
      } else if (includeLeaderboard) {
        // If no window yet, just show empty until next render tick
        mergeRoot({ leaderboard: [] });
        updateLoading({ leaderboard: false });
      }

      // --- 4) RECENT RESULTS (fully completed games/props) ---
      updateLoading({ recent: true });
      tasks.push(
        fetchJSON('/analytics/api/recent-results/?limit=10')
          .then((data) => {
            const patch = { recentGames: Array.isArray(data?.results) ? data.results : [] };
            mergeUserData(patch);
          })
          .catch((e) => { setError((prev) => prev || e.message); })
          .finally(() => updateLoading({ recent: false }))
      );

      // --- 5) INSIGHTS (map to user timeline for now) ---
      updateLoading({ insights: true });
      tasks.push(
        fetchJSON('/analytics/api/user-timeline/')
          .then((data) => {
            // Expose as insights to keep existing consumers working
            mergeRoot({ insights: Array.isArray(data?.timeline) ? data.timeline : [] });
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

  const api = useMemo(
    () => ({ dashboardData, loadingStates, error, reload }),
    [dashboardData, loadingStates, error, reload]
  );

  return api;
}
