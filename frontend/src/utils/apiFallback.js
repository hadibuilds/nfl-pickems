// Centralized adapters for the new analytics fallback endpoints
// ⚠️ Pure logic – no styling touched.

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// --- Season Performance (current user or a given user) ---
export async function fetchSeasonPerformance({ userId = null } = {}) {
  const url = new URL(`${API_BASE}/analytics/api/fallback/season-performance/`);
  if (userId) url.searchParams.set('user_id', userId);

  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`Season performance fetch failed: ${res.status}`);
  const data = await res.json();

  // Map backend → UI shape your components already use
  // (names taken from your fallback view: moneyline_accuracy, prop_accuracy, overall_accuracy, total_points, correct_ml, correct_props, total_ml, total_props)
  return {
    mlAccuracy: data.moneyline_accuracy ?? 0,     // %
    propAccuracy: data.prop_accuracy ?? 0,        // %
    overallAccuracy: data.overall_accuracy ?? 0,  // %
    totalPoints: data.total_points ?? 0,
    correctML: data.correct_ml ?? 0,
    correctProps: data.correct_props ?? 0,
    totalML: data.total_ml ?? 0,
    totalProps: data.total_props ?? 0,
  };
}

// --- Top N leaderboard (fallback) ---
export async function fetchTopNLeaderboard({ limit = 3 } = {}) {
  const url = new URL(`${API_BASE}/analytics/api/fallback/leaderboard/`);
  url.searchParams.set('limit', String(limit));

  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error(`Leaderboard fetch failed: ${res.status}`);
  const data = await res.json();

  // Expecting: { leaderboard: [{ username, total_points, ... }], meta: {...} }
  // Map to the minimal shape your existing leaderboard/standings UI reads.
  const items = (data.leaderboard || []).map((row, idx) => ({
    username: row.username,
    totalPoints: row.total_points ?? 0,
    rank: row.rank ?? idx + 1, // keep dense rank if provided; fallback to 1..N
    isCurrentUser: !!row.is_current_user,
    mlCorrect: row.correct_ml ?? 0,
    propsCorrect: row.correct_props ?? 0,
    mlTotal: row.total_ml ?? 0,
    propsTotal: row.total_props ?? 0,
    // add any other fields your UI currently reads (but keep names stable here)
  }));

  return { items, meta: data.meta || {} };
}
