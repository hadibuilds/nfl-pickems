/*
 * HomePage: season rings + trend arrows everywhere
 * - Season rings: /predictions/api/user-season-stats-fast/
 * - Rank trend card: /predictions/api/user-trends-fast/?weeks=2
 * - Leaderboard WITH arrows: now uses /predictions/api/home-top3/ (dense ties + snapshot trend)
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useAuthWithNavigation } from '../hooks/useAuthWithNavigation.js';
import useDashboardData from '../hooks/useDashboardData.js';
import PageLayout from '../components/common/PageLayout.jsx';
import UserAvatar from '../components/common/UserAvatar.jsx';
import { TrendingUp, TrendingDown, Trophy, Target, Clock, Users, Zap } from 'lucide-react';
import {
  GoldMedal,
  SilverMedal,
  BronzeMedal,
  capitalizeFirstLetter,
  calculateRankWithTies,
  getMedalTier,
} from '../components/standings/rankingUtils.jsx';
import { getCookie } from '../utils/cookies.js';
import confetti from 'canvas-confetti';

const ProgressRing = ({ percentage, size = 120, strokeWidth = 8, showPercentage = true, fontSize = 'text-2xl' }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = `${circumference} ${circumference}`;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgba(139, 92, 246, 0.1)" strokeWidth={strokeWidth} fill="transparent" />
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="url(#gradient)" strokeWidth={strokeWidth} fill="transparent"
          strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} strokeLinecap="round"
          className="transition-all duration-1000 ease-out" />
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8B5CF6" /><stop offset="100%" stopColor="#7C3AED" />
          </linearGradient>
        </defs>
      </svg>
      {showPercentage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-bold text-white ${fontSize}`}>{Math.round(Number(percentage))}%</span>
        </div>
      )}
    </div>
  );
};

const StatCard = ({ title, value, subtitle, icon: Icon, trend, color = "blue" }) => {
  const colorClasses = {
    blue: "from-blue-500 to-blue-600", purple: "from-purple-500 to-purple-600",
    green: "from-green-500 to-green-600", orange: "from-orange-500 to-orange-600", red: "from-red-500 to-red-600"
  };
  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-2xl p-6 text-white shadow-lg`}>
      <div className="flex items-center justify-between">
        <Icon className="w-8 h-8 opacity-80" />
        {trend && trend !== 'same' && (
          <div className={`flex items-center text-sm ${trend === 'up' ? 'text-green-200' : 'text-red-200'}`}>
            {trend === 'up' ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
          </div>
        )}
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm opacity-90">{title}</div>
      {subtitle && <div className="text-xs opacity-70 mt-1">{subtitle}</div>}
    </div>
  );
};

const LeaderboardRow = ({ entry, standingsForMedals }) => {
  const medalTier = getMedalTier(standingsForMedals, entry.username);
  const rank = calculateRankWithTies(standingsForMedals, entry.username);

  // derive trend if server only sent rank_change
  const derivedTrend =
    entry?.trend ??
    (typeof entry?.rank_change === 'number'
      ? (entry.rank_change > 0 ? 'up' : entry.rank_change < 0 ? 'down' : 'same')
      : 'same');

  const renderRankBadge = (tier) => {
    if (tier === 1) return <GoldMedal />;
    if (tier === 2) return <SilverMedal />;
    if (tier === 3) return <BronzeMedal />;
    return <div className="w-5 h-5 bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold text-white">{rank}</div>;
  };

  return (
    <div className={`flex items-center justify-between p-3 rounded-lg ${entry.isCurrentUser ? 'bg-purple-500/20 border border-purple-500/30' : 'hover:bg-gray-700/50'}`}>
      <div className="flex items-center space-x-3">
        <UserAvatar username={entry.username} size="sm" className="w-8 h-8 flex-shrink-0" />
        <div className="flex items-center justify-center">{renderRankBadge(medalTier)}</div>
        <div>
          <div className={`font-medium text-sm ${entry.isCurrentUser ? 'text-purple-300' : 'text-white'}`}>
            {capitalizeFirstLetter(entry.username)}
          </div>
          <div className="text-xs" style={{ color: '#9ca3af' }}>{entry.total_points ?? entry.points ?? 0} points</div>
        </div>
      </div>
      <div className="flex items-center text-sm">
        {derivedTrend !== 'same' && (
          <div className={`flex items-center text-sm ${derivedTrend === 'up' ? 'text-green-200' : 'text-red-200'}`}>
            {derivedTrend === 'up'
              ? <TrendingUp className="w-4 h-4 mr-1" />
              : <TrendingDown className="w-4 h-4 mr-1" />}
          </div>
        )}
      </div>
    </div>
  );
};

function HomePage() {
  const { userInfo, navigate } = useAuthWithNavigation();
  // Weekly/live tiles
  const { dashboardData, error } = useDashboardData(userInfo, {
    loadGranular: true,
    includeLeaderboard: false,
  });

  // Season (snapshot) performance
  const [seasonPerf, setSeasonPerf] = useState({ overall: 0, ml: 0, prop: 0, totalPoints: 0, loaded: false });
  // Weekly rank trend for the stat card
  const [rankMeta, setRankMeta] = useState({ trend: 'same', rankChange: 0 });

  // Top-3 leaderboard from /predictions/api/home-top3/
  const [items, setItems] = useState([]);
  const [top3Loading, setTop3Loading] = useState(true);
  const [top3Err, setTop3Err] = useState(null);

  const API_BASE = import.meta.env.VITE_API_URL;

  // Season performance
  useEffect(() => {
    if (!userInfo) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/predictions/api/user-season-stats-fast/`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!res.ok) throw new Error('user-season-stats-fast failed');
        const s = await res.json();
        setSeasonPerf({
          overall: Number(s?.current_season_accuracy ?? 0),
          ml: Number(s?.current_moneyline_accuracy ?? 0),
          prop: Number(s?.current_prop_accuracy ?? 0),
          totalPoints: Number(s?.current_season_points ?? 0),
          loaded: true
        });
        if (typeof s?.trending_direction === 'string') {
          setRankMeta((prev) => ({ ...prev, trend: s.trending_direction }));
        }
      } catch (e) {
        console.warn(e);
        setSeasonPerf((p) => ({ ...p, loaded: true }));
      }
    })();
  }, [userInfo, API_BASE]);

  // Rank trend for stat card
  useEffect(() => {
    if (!userInfo) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/predictions/api/user-trends-fast/?weeks=2`, {
          credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!res.ok) throw new Error('user-trends-fast failed');
        const data = await res.json();
        const arr = Array.isArray(data?.trends) ? data.trends : [];
        if (arr.length >= 2) {
          const latest = arr[arr.length - 1];
          const prev = arr[arr.length - 2];
          const change = (prev?.rank && latest?.rank) ? (prev.rank - latest.rank) : 0; // lower is better
          const trend = change > 0 ? 'up' : change < 0 ? 'down' : 'same';
          setRankMeta({ trend, rankChange: Math.abs(change) });
        } else if (arr.length === 1) {
          setRankMeta({ trend: arr[0]?.trend || 'same', rankChange: Math.abs(arr[0]?.rank_change || 0) });
        }
      } catch (e) {
        console.warn(e);
      }
    })();
  }, [userInfo, API_BASE]);

  // Fetch Top-3 live leaderboard (dense ties)
  useEffect(() => {
    if (!userInfo) return;
    let alive = true;
    (async () => {
      try {
        setTop3Err(null);
        setTop3Loading(true);
        const res = await fetch(`${API_BASE}/insights/api/home-top3/`, { credentials: 'include' });
        if (!res.ok) throw new Error('home-top3 failed');
        const data = await res.json();
        const list = Array.isArray(data?.items) ? data.items : [];
        const marked = list.map(r => ({
          ...r,
          isCurrentUser: String(r.username) === String(userInfo?.username),
        }));
        if (alive) setItems(marked);
      } catch (e) {
        console.warn(e);
        if (alive) {
          setItems([]);
          setTop3Err(e.message || 'Failed to load Top-3');
        }
      } finally {
        if (alive) setTop3Loading(false);
      }
    })();
    return () => { alive = false; };
  }, [userInfo, API_BASE]);

  if (!userInfo) {
    return (
      <div className="pt-16">
        <h2>you are not logged in</h2>
        <p className="text-center text-small"><a href="/login" style={{ color: '#8B5CF6', fontSize: '16px' }}>Login</a></p>
        <p className="text-center text-small"><a href="/signup" style={{ color: '#8B5CF6', fontSize: '16px' }}>Sign Up</a></p>
      </div>
    );
  }

  if (error) {
    return (
      <PageLayout>
        <div className="text-center py-8">
          <p className="text-red-400">Error loading dashboard: {error}</p>
          <button className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </PageLayout>
    );
  }

  // Build a medal/rank list for helpers, preserving trend
  const standingsForMedals = useMemo(() => {
    const sorted = [...items].sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0));
    return sorted.map(s => ({ username: s.username, total_points: s.total_points }));
  }, [items]);

  const goToWeeks = () => {
    confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
    navigate('/weeks');
  };

  const userData = dashboardData?.user_data || {};

  return (
    <PageLayout>
      {/* Header */}
      <div className="mb-6 text-center">
        <h2 className="text-2xl sm:text-3xl font-bold mb-2">
          Welcome back, <span style={{ color: '#8B5CF6' }}>{userInfo.username}</span>!
        </h2>
        <p style={{ color: '#9ca3af', fontSize: '14px' }}>
          Week {userData.currentWeek} • Ready to make your picks?
        </p>
      </div>

      {/* Weekly/Live Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard title="Current Rank" value={`#${userData.rank ?? '—'}`} subtitle={`+${rankMeta.rankChange || 0} this week`} icon={Trophy} trend={rankMeta.trend} color="purple" />
        <StatCard title="Pending Picks" value={userData.pendingPicks || 0} subtitle="for this week" icon={Clock} color="blue" />
        <StatCard title="Points Behind" value={userData.pointsFromLeader || 0} subtitle="from 1st place" icon={Target} color="orange" />
        <StatCard title="Best Category" value={userData.bestCategory === 'Moneyline' ? '$-line' : userData.bestCategory || 'N/A'} subtitle={`${userData.bestCategoryAccuracy || 0}% accuracy`} icon={Zap} color="green" />
      </div>

      {/* Season Performance + Leaderboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {/* Season Performance Rings */}
        <div className="rounded-2xl p-4 flex flex-col items-center justify-center mb-6">
          <h3 className="text-lg font-semibold">Season Performance</h3>
          <div className="flex space-x-4 items-center">
            <div className="flex flex-col items-center">
              <ProgressRing percentage={seasonPerf.overall || 0} size={80} strokeWidth={6} fontSize="text-base" />
              <div className="mt-2 text-center"><div className="text-xs font-bold" style={{ color: '#C2185B' }}>Overall</div></div>
            </div>
            <div className="flex flex-col items-center">
              <ProgressRing percentage={seasonPerf.ml || 0} size={80} strokeWidth={6} showPercentage fontSize="text-base" />
              <div className="mt-2 text-center"><div className="text-xs font-bold text-green-400">Moneyline</div></div>
            </div>
            <div className="flex flex-col items-center">
              <ProgressRing percentage={seasonPerf.prop || 0} size={80} strokeWidth={6} showPercentage fontSize="text-base" />
              <div className="mt-2 text-center"><div className="text-xs font-bold text-blue-400">Prop Bets</div></div>
            </div>
          </div>
          <div className="mt-4 text-center">
            <div className="text-2xl font-bold" style={{ color: "#F9A825" }}>
              {seasonPerf.totalPoints || 0}
            </div>
            <div className="text-sm" style={{ color: '#9ca3af' }}>Total Points (season)</div>
          </div>
        </div>

        {/* Leaderboard (with trend arrows) */}
        <div className="rounded-2xl p-4 mb-6" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Leaderboard</h3>
            <Users className="w-4 h-4" style={{ color: '#9ca3af' }} />
          </div>
          <div className="space-y-0">
            {top3Loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
              </div>
            ) : top3Err ? (
              <div className="text-center py-4" style={{ color: '#ef4444' }}>
                Couldn’t load Top-3. Try again.
              </div>
            ) : items.length === 0 ? (
              <div className="text-center py-4" style={{ color: '#9ca3af' }}>
                No results yet.
              </div>
            ) : (
              <>
                {items.map((entry, idx) => (
                  <LeaderboardRow key={entry.user_id ?? entry.username ?? idx} entry={entry} standingsForMedals={standingsForMedals} />
                ))}
              </>
            )}
          </div>
          <button className="w-full mt-3 text-xs font-medium transition-colors hover:text-purple-300" style={{ color: '#8B5CF6' }} onClick={() => navigate('/standings')}>
            View Full Standings →
          </button>
        </div>

        {/* Recent Games */}
        <div className="rounded-2xl p-4 mb-6" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Recent Games</h3>
            <Clock className="w-4 h-4" style={{ color: '#9ca3af' }} />
          </div>
          <div className="space-y-3">
            {(dashboardData?.user_data?.recentGames || []).slice(0, 2).map(game => (
              <div key={game.id} className={`p-4 rounded-lg border-l-4 transition-all duration-200 ${game.correct ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'}`} style={{ backgroundColor: game.correct ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="text-sm font-medium" style={{ color: '#9ca3af' }}>{game.awayTeam} @ {game.homeTeam}</div>
                    <div className={`text-xs px-2 py-1 rounded-full ${game.correct ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>{game.correct ? '✓' : '✗'}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-white">+{game.points} pts</div>
                    <div className="text-xs" style={{ color: '#9ca3af' }}>Pick: {game.userPick}</div>
                  </div>
                </div>
              </div>
            ))}
            {(!dashboardData?.user_data?.recentGames || dashboardData.user_data.recentGames.length === 0) && (
              <div className="text-center py-4" style={{ color: '#9ca3af' }}>
                <p>No recent completed games</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="flex justify-center">
        <button className="px-6 py-3 rounded-2xl text-white font-semibold text-base transition-all duration-200 hover:scale-105 shadow-lg inline-flex items-center space-x-2"
          style={{ background: 'linear-gradient(135deg, #8B5CF6, #7C3AED)' }} onClick={goToWeeks}>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
          </svg>
          <span>View All Games</span>
        </button>
      </div>
    </PageLayout>
  );
}

export default HomePage;
