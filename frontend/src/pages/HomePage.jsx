/*
 * HomePage: season rings + trend arrows everywhere
 * (now backed by analytics endpoints)
 * - Season rings: /analytics/accuracy_summary/
 * - Rank & points-behind & pending picks (week): /analytics/stats_summary/
 * - Leaderboard WITH arrows (rank_delta from snapshots): /analytics/leaderboard/?window_key=...
 * - Recent Games (fully completed): /analytics/recent_results/?limit=10
 */

import React, { useEffect, useMemo, useState } from 'react';
import '../RecentGamesScrollbar.css';
import { useAuthWithNavigation } from '../hooks/useAuthWithNavigation';
import useDashboardData from '../hooks/useDashboardData';
import PageLayout from '../components/common/PageLayout';
import UserAvatar from '../components/common/UserAvatar';
import { TrendingUp, TrendingDown, Trophy, Target, Clock, Users, Zap, Eye } from 'lucide-react';
import {
  GoldMedal,
  SilverMedal,
  BronzeMedal,
  capitalizeFirstLetter,
  calculateRankWithTies,
  getMedalTier,
} from '../components/standings/rankingUtils.jsx';
import { getCookie } from '../utils/cookies';

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

const StatCard = ({ title, value, subtitle, icon: Icon, trend, color = "blue", onClick, clickable = false }) => {
  const colorClasses = {
    blue: "from-blue-500 to-blue-600", purple: "from-purple-500 to-purple-600",
    green: "from-green-500 to-green-600", orange: "from-orange-500 to-orange-600", red: "from-red-500 to-red-500"
  };
  
  const baseClasses = `bg-gradient-to-br ${colorClasses[color]} rounded-2xl p-6 text-white shadow-lg transition-all duration-200`;
  const interactiveClasses = clickable ? `${baseClasses} cursor-pointer hover:scale-105 hover:shadow-xl active:scale-95` : baseClasses;
  
  const CardContent = () => (
    <>
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
    </>
  );
  
  return clickable ? (
    <button className={interactiveClasses} onClick={onClick} type="button">
      <CardContent />
    </button>
  ) : (
    <div className={interactiveClasses}>
      <CardContent />
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
        <UserAvatar username={entry.username} profilePicture={entry.avatar} size="sm" className="w-8 h-8 flex-shrink-0" />
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
  // legacy hook still used for error/loading guards; we’ll overlay our own data
  const { dashboardData, error } = useDashboardData(userInfo, {
    loadGranular: true,
    includeLeaderboard: false,
  });

  // Local home data overlayed onto existing UI bindings
  const [homeUserData, setHomeUserData] = useState({
    currentWeek: null,
    rank: null,
    pointsFromLeader: 0,
    pendingPicks: 0,
    bestCategory: 'N/A',
    bestCategoryAccuracy: 0,
    recentGames: [],
  });

  // Season (snapshot) performance rings
  const [seasonPerf, setSeasonPerf] = useState({ overall: 0, ml: 0, prop: 0, totalPoints: 0, loaded: false });

  // Weekly rank trend for the stat card (keep default for now)
  const [rankMeta, setRankMeta] = useState({ trend: 'same', rankChange: 0 });

  // Leaderboard (with trend/rank_delta)
  const [standings, setStandings] = useState([]);
  const [standingsLoaded, setStandingsLoaded] = useState(false);

  // anchor window key for the season-to-date leaderboard
  const [anchorWindowKey, setAnchorWindowKey] = useState(null);
  
  // Last updated timestamp
  const [lastUpdated, setLastUpdated] = useState(null);

  const API_BASE = import.meta.env.VITE_API_URL;

  // 1) Stats header + Season performance + Leaderboard (sequential calls)
  useEffect(() => {
    if (!userInfo) return;
    (async () => {
      try {
        // Stats header
        const statsRes = await fetch(`${API_BASE}/analytics/api/stats-summary/`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!statsRes.ok) throw new Error('stats_summary failed');
        const stats = await statsRes.json();

        // Accuracy (season rings + best category)
        const accRes = await fetch(`${API_BASE}/analytics/api/accuracy-summary/`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!accRes.ok) throw new Error('accuracy_summary failed');
        const acc = await accRes.json();

        // season rings
        setSeasonPerf({
          overall: Number((acc?.overallAccuracy ?? 0) * 100),
          ml: Number((acc?.moneylineAccuracy ?? 0) * 100),
          prop: Number((acc?.propBetAccuracy ?? 0) * 100),
          totalPoints: Number(acc?.totalPoints ?? 0),
          loaded: true
        });

        // best category + header tiles
        setHomeUserData((prev) => ({
          ...prev,
          currentWeek: stats?.currentWeek ?? null,
          rank: stats?.rank ?? null,
          pointsFromLeader: stats?.pointsFromLeader ?? 0,
          // backend exposes pendingPicksWeek; map to UI's "Pending Picks"
          pendingPicks: stats?.pendingPicksWeek ?? 0,
          bestCategory: acc?.bestCategory || 'N/A',
          bestCategoryAccuracy: Number(acc?.bestCategoryAccuracy || 0)
        }));

        // Get window key and fetch leaderboard immediately
        const windowKey = stats?.window?.key;
        if (windowKey) {
          setAnchorWindowKey(windowKey);
          
          // Fetch leaderboard with the window key
          try {
            const leaderRes = await fetch(
              `${API_BASE}/analytics/api/leaderboard/?window_key=${encodeURIComponent(windowKey)}&limit=3`,
              { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } }
            );
            if (leaderRes.ok) {
              const leaderData = await leaderRes.json();
              const rows = Array.isArray(leaderData?.leaderboard) ? leaderData.leaderboard : [];

              const marked = rows.map(r => ({
                username: r.username,
                avatar: r.avatar,
                total_points: r.total_points,
                rank_dense: r.rank_dense,
                rank_change: r.rank_delta,
                isCurrentUser: String(r.username) === String(userInfo?.username),
              }));
              setStandings(marked);
            } else {
              console.warn('Leaderboard fetch failed:', leaderRes.status);
              setStandings([]);
            }
          } catch (leaderError) {
            console.warn('Leaderboard error:', leaderError);
            setStandings([]);
          } finally {
            setStandingsLoaded(true);
          }
        } else {
          // Fallback: try to get leaderboard without window_key (use current window)
          try {
            const leaderRes = await fetch(
              `${API_BASE}/analytics/api/leaderboard/?limit=3`,
              { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } }
            );
            if (leaderRes.ok) {
              const leaderData = await leaderRes.json();
              const rows = Array.isArray(leaderData?.leaderboard) ? leaderData.leaderboard : [];
              const marked = rows.map(r => ({
                username: r.username,
                avatar: r.avatar,
                total_points: r.total_points,
                rank_dense: r.rank_dense,
                rank_change: r.rank_delta,
                isCurrentUser: String(r.username) === String(userInfo?.username),
              }));
              setStandings(marked);
            } else {
              setStandings([]);
            }
          } catch (fallbackError) {
            setStandings([]);
          } finally {
            setStandingsLoaded(true);
          }
        }
        
        // Set last updated timestamp after all data loads
        setLastUpdated(new Date());
      } catch (e) {
        console.warn(e);
        setSeasonPerf((p) => ({ ...p, loaded: true }));
        setStandings([]);
        setStandingsLoaded(true);
        setLastUpdated(new Date());
      }
    })();
  }, [userInfo, API_BASE]);

  // 3) Recent fully completed games
  useEffect(() => {
    if (!userInfo) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics/api/recent-results/?limit=10`, {
          credentials: 'include',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (!res.ok) throw new Error('recent_results failed');
        const data = await res.json();
        const results = Array.isArray(data?.results) ? data.results : [];
        setHomeUserData((prev) => ({ ...prev, recentGames: results }));
      } catch (e) {
        console.warn(e);
        setHomeUserData((prev) => ({ ...prev, recentGames: [] }));
      }
    })();
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
    const sorted = [...standings].sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0));
    return sorted.map(s => ({ username: s.username, total_points: s.total_points }));
  }, [standings]);

  const goToWeeks = () => {
    navigate('/weeks');
  };

  // Prefer our local overlay; fall back to hook data if needed (keeps JSX unchanged)
  const userData = homeUserData || dashboardData?.user_data || {};

  return (
    <PageLayout>
      {/* Header */}
      <div className="mb-6 text-center">
        <h1 className="font-bebas text-4xl sm:text-5xl md:text-6xl font-bold mb-2 tracking-wider">
          Welcome back, <span style={{ color: '#8B5CF6' }}>{userInfo.first_name || userInfo.username}</span>!
        </h1>
        <p style={{ color: '#9ca3af', fontSize: '14px' }}>
          Week {userData.currentWeek} • Ready to make your picks?
        </p>
      </div>

      {/* Weekly/Live Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard title="Current Rank" value={`#${userData.rank ?? '—'}`} subtitle={`+${rankMeta.rankChange || 0} this week`} icon={Trophy} trend={rankMeta.trend} color="green" />
        <StatCard 
          title="Pending Picks" 
          value={userData.pendingPicks || 0} 
          subtitle="for this week" 
          icon={Clock} 
          color="purple" 
          clickable={true}
          onClick={() => navigate(`/week/${userData.currentWeek}`)}
        />
        <StatCard 
          title="Points Behind" 
          value={userData.pointsFromLeader || 0} 
          subtitle="from 1st place" 
          icon={Target} 
          color="orange"
          clickable={true}
          onClick={() => navigate('/peek')}
        />
        <StatCard title="Best Category" value={userData.bestCategory === 'Moneyline' ? '$-line' : userData.bestCategory || 'N/A'} subtitle={`${userData.bestCategoryAccuracy || 0}% accuracy`} icon={Eye} color="blue" />
      </div>

      {/* Season Performance + Leaderboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6 homepage-grid-equal-height">
        {/* Season Performance Rings */}
        <div className="homepage-glass-section season-performance-glass p-4">
          <div className="homepage-glass-content h-full flex flex-col">
            <h3 className="homepage-section-title text-center">Season Performance</h3>
            <div className="flex-1 flex flex-col justify-center">
              <div className="flex space-x-3 items-center justify-center">
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
                <div className="text-sm homepage-section-content" style={{ color: '#9ca3af' }}>Total Points (season)</div>
              </div>
            </div>
          </div>
        </div>

        {/* Leaderboard (with trend arrows) */}
        <div className="homepage-glass-section p-4">
          <div className="homepage-glass-content">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <h3 className="homepage-section-title">Leaderboard</h3>
              {/*{lastUpdated && (
                  <span className="homepage-section-content" style={{ color: '#6b7280', fontSize: '11px', fontFamily: 'roboto-condensed, sans-serif' }}>
                    Updated @ {lastUpdated.toLocaleTimeString('en-US', { 
                      hour12: false, 
                      hour: '2-digit', 
                      minute: '2-digit',
                    })}
                  </span>
                )} */}
              </div>
              <Users className="w-4 h-4" style={{ color: '#9ca3af' }} />
            </div>
            <div className="space-y-0">
              {!standingsLoaded ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                </div>
              ) : standings.length > 0 ? (
                <>
                  {standings.map((entry, idx) => (
                    <LeaderboardRow key={entry.username || idx} entry={entry} standingsForMedals={standingsForMedals} />
                  ))}
                </>
              ) : (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm homepage-section-content" style={{ color: '#9ca3af' }}>
                    No game results, check back later
                  </p>
                </div>
              )}
            </div>
            <button className="w-full mt-3 text-xs font-medium transition-colors hover:text-purple-300 homepage-section-content" style={{ color: '#8B5CF6' }} onClick={() => navigate('/standings')}>
              View Full Standings →
            </button>
          </div>
        </div>

        {/* Recent Games */}
        <div className="homepage-glass-section p-4" style={{ height: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div className="homepage-glass-content">
            <div className="flex items-center justify-between mb-4">
              <h3 className="homepage-section-title">Recent Games</h3>
              <Clock className="w-4 h-4" style={{ color: '#9ca3af' }} />
            </div>
            <div 
              className="space-y-3 recent-games-scrollable homepage-section-content" 
              style={{ 
                flex: '1 1 0%',
                overflowY: 'auto',
                overflowX: 'hidden',
                paddingRight: '4px',
                scrollbarWidth: 'thin',
                scrollbarColor: '#4B5563 #2d2d2d',
                WebkitOverflowScrolling: 'touch',
                minHeight: '0'
              }}
            >
              {(userData?.recentGames || []).map(game => {
                // Handle the new 3-way color logic
                const status = game.correctStatus || (game.correct ? 'full' : 'none');
                const isGreen = status === 'full';
                const isYellow = status === 'partial';
                
                const borderColor = isGreen ? 'border-green-500' : isYellow ? 'border-yellow-500' : 'border-red-500';
                const bgColor = isGreen ? 'rgba(16, 185, 129, 0.1)' : isYellow ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)';
                const badgeBg = isGreen ? 'bg-green-500/20' : isYellow ? 'bg-yellow-500/20' : 'bg-red-500/20';
                const badgeText = isGreen ? 'text-green-300' : isYellow ? 'text-yellow-300' : 'text-red-300';
                const badge = isGreen ? '✓' : isYellow ? '◐' : '✗';
                
                return (
                  <div key={game.id} className={`p-4 rounded-lg border-l-4 transition-all duration-200 ${borderColor}`} style={{ backgroundColor: bgColor }}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="text-sm font-medium homepage-section-content" style={{ color: '#9ca3af' }}>{game.awayTeam} @ {game.homeTeam}</div>
                        <div className={`text-xs px-2 py-1 rounded-full ${badgeBg} ${badgeText}`}>{badge}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-white">+{game.points} pts</div>
                        <div className="text-xs homepage-section-content" style={{ color: '#9ca3af' }}>Pick: {game.userPick}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
              {(!userData?.recentGames || userData.recentGames.length === 0) && (
                <div className="text-center py-4 homepage-section-content" style={{ color: '#9ca3af' }}>
                  <p>No recent completed games</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="flex justify-center">
        <button 
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700 text-white font-semibold rounded-2xl transition-all duration-200 hover:scale-105 shadow-lg inline-flex items-center space-x-2"
          onClick={goToWeeks}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="12" cy="12" rx="6" ry="9" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M12 3v18M5.5 7.5l13 0M5.5 16.5l13 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <span>View All Games</span>
        </button>
      </div>
    </PageLayout>
  );
}

export default HomePage;
