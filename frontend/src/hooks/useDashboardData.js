// useDashboardData.js
import { useEffect, useMemo, useState } from 'react';

/**
 * Generic helper: try a list of URLs in order; return the first OK JSON.
 * If all fail (network, 404, non-2xx), return null.
 */
async function fetchFirstOk(urls, opts = {}) {
  for (const url of urls) {
    try {
      const res = await fetch(url, opts);
      if (!res.ok) continue; // move to next candidate
      const json = await res.json();
      return json;
    } catch (_) {
      // swallow and try next
    }
  }
  return null;
}

/**
 * Normalizers
 * Keep your UI props stable by adapting differing API payloads into
 * a single, predictable shape the components already use.
 */

// Leaderboard: unify "windowed" & "snapshot" formats to [{ user, points, mlPoints, propPoints, rank, trend }, ...]
function normalizeTop3(payload) {
  if (!payload) return { list: [], message: 'No results yet. Check back later.' };

  // Common possibilities:
  // - { top3: [...], meta: {...} }
  // - { results: [...], window_key: '...' }
  // - plain array: [...]
  const list = Array.isArray(payload) ? payload
    : Array.isArray(payload?.top3) ? payload.top3
    : Array.isArray(payload?.results) ? payload.results
    : [];

  const mapped = list.map((row, i) => ({
    user: row.user ?? row.username ?? row.display_name ?? 'Unknown',
    points: Number(row.total_points ?? row.points ?? 0),
    mlPoints: Number(row.ml_points ?? row.ml ?? 0),
    propPoints: Number(row.prop_points ?? row.prop ?? 0),
    rank: Number(row.rank ?? i + 1),
    trend: row.trend ?? row.trending_direction ?? null,
  }));

  const message = mapped.length ? null : (payload?.message || 'No results yet. Check back later.');
  return { list: mapped, message };
}

// Season performance: unify to { overall, ml, prop, totalPoints, loaded }
function normalizeSeasonPerf(s) {
  if (!s) return { overall: 0, ml: 0, prop: 0, totalPoints: 0, loaded: true };

  return {
    overall: Number(s.current_season_accuracy ?? s.overall_accuracy ?? 0),
    ml: Number(s.current_moneyline_accuracy ?? s.ml_accuracy ?? 0),
    prop: Number(s.current_prop_accuracy ?? s.prop_accuracy ?? 0),
    totalPoints: Number(s.current_season_points ?? s.total_points ?? 0),
    loaded: true,
  };
}

// Week/meta: unify to { week, season, windowKey, label }
function normalizeWeekMeta(m) {
  if (!m) return { week: null, season: null, windowKey: null, label: null };

  const week = Number(m.week ?? m.current_week ?? m.week_number ?? null);
  const season = Number(m.season ?? m.season_year ?? null);
  const windowKey = m.window_key ?? m.windowKey ?? null;
  const label = m.label ?? (week ? `Week ${week}` : null);

  return { week, season, windowKey, label };
}

/**
 * ROUTE CANDIDATES
 * New analytics first, then legacy fallbacks.
 * Adjust paths here as you finalize your analytics URLs.
 */
function makeRoutes(API_BASE) {
  return {
    leaderboardTop3: [
      // Primary (windowed “new brain”)
      `${API_BASE}/analytics/api/windowed-top3/`,
      // Secondary (analytics snapshot, if you kept it)
      `${API_BASE}/analytics/api/home-top3/`,
      // Legacy predictions snapshot
      `${API_BASE}/predictions/api/home-top3/`,
      // Legacy insights (if still around — harmless if 404)
      `${API_BASE}/insights/api/home-top3/`,
    ],
    seasonStats: [
      `${API_BASE}/analytics/api/user-season-stats/`,
      `${API_BASE}/predictions/api/user-season-stats-fast/`,
    ],
    weekMeta: [
      // prefer analytics
      `${API_BASE}/analytics/api/season-week/`,
      `${API_BASE}/analytics/api/season-meta/`,
      // game/predictions legacy fallbacks
      `${API_BASE}/games/api/current-week/`,
      `${API_BASE}/predictions/api/current-week/`,
    ],
  };
}

/**
 * Public hook: signature preserved for drop-in use on the HomePage.
 *
 * Exposes:
 * - top3       : normalized list of top-3 rows
 * - top3Msg    : friendly message if empty
 * - top3Loaded : boolean
 * - seasonPerf : { overall, ml, prop, totalPoints, loaded }
 * - weekInfo   : { week, season, windowKey, label }
 * - error      : final non-fatal string (we default to soft success w/ empty data)
 */
export default function useDashboardData({ API_BASE, userInfo }) {
  const ROUTES = useMemo(() => makeRoutes(API_BASE), [API_BASE]);

  const [top3, setTop3] = useState([]);
  const [top3Msg, setTop3Msg] = useState(null);
  const [top3Loaded, setTop3Loaded] = useState(false);

  const [seasonPerf, setSeasonPerf] = useState({ overall: 0, ml: 0, prop: 0, totalPoints: 0, loaded: false });
  const [weekInfo, setWeekInfo] = useState({ week: null, season: null, windowKey: null, label: null });

  const [error, setError] = useState(null);

  // Leaderboard (top-3)
  useEffect(() => {
    let alive = true;
    (async () => {
      const payload = await fetchFirstOk(ROUTES.leaderboardTop3);
      if (!alive) return;

      const { list, message } = normalizeTop3(payload);
      setTop3(list);
      setTop3Msg(message || null);
      setTop3Loaded(true);
      // No hard error; if empty, UI still renders gracefully
    })().catch((e) => {
      if (!alive) return;
      console.warn(e);
      setTop3([]);
      setTop3Msg('No results yet. Check back later.');
      setTop3Loaded(true);
      setError((prev) => prev ?? 'leaderboard');
    });
    return () => { alive = false; };
  }, [ROUTES.leaderboardTop3]);

  // Season performance (requires user)
  useEffect(() => {
    if (!userInfo) return;
    let alive = true;
    (async () => {
      const s = await fetchFirstOk(ROUTES.seasonStats);
      if (!alive) return;
      setSeasonPerf(normalizeSeasonPerf(s));
    })().catch((e) => {
      if (!alive) return;
      console.warn(e);
      setSeasonPerf((p) => ({ ...p, loaded: true }));
      setError((prev) => prev ?? 'season');
    });
    return () => { alive = false; };
  }, [userInfo, ROUTES.seasonStats]);

  // Week/meta
  useEffect(() => {
    let alive = true;
    (async () => {
      const m = await fetchFirstOk(ROUTES.weekMeta);
      if (!alive) return;
      setWeekInfo(normalizeWeekMeta(m));
    })().catch((e) => {
      if (!alive) return;
      console.warn(e);
      setWeekInfo({ week: null, season: null, windowKey: null, label: null });
      setError((prev) => prev ?? 'week');
    });
    return () => { alive = false; };
  }, [ROUTES.weekMeta]);

  return {
    top3,
    top3Msg,
    top3Loaded,
    seasonPerf,
    weekInfo,
    error,
  };
}
