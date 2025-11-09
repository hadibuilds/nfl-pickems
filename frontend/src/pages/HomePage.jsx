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
import { TrendingUp, TrendingDown, Trophy, Target, Clock, Users, Eye, ThumbsUp, Footprints } from 'lucide-react';
import {
  GoldMedal,
  SilverMedal,
  BronzeMedal,
  capitalizeFirstLetter,
  calculateRankWithTies,
  getMedalTier,
} from '../components/standings/rankingUtils.jsx';
import { getCookie } from '../utils/cookies';

const PerformanceBar = ({ label, percentage, color = "#8B5CF6" }) => {
  const displayPercentage = Math.round(Number(percentage) || 0);

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-xs font-medium opacity-70 min-w-[90px] text-left">{label}</div>
      <div className="flex-1 relative h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${displayPercentage}%`,
            background: `linear-gradient(to right, ${color}, ${color}dd)`
          }}
        />
      </div>
      <div className="text-xs font-semibold min-w-[35px] text-right">{displayPercentage}%</div>
    </div>
  );
};

const StatCard = ({ title, value, subtitle, icon: Icon, trend, color = "blue", onClick, clickable = false, weekBadge }) => {
  const colorClasses = {
    blue: "from-blue-500 via-blue-600 to-indigo-700",
    purple: "from-purple-500 via-purple-600 to-violet-700",
    green: "from-green-500 via-emerald-600 to-teal-700",
    orange: "from-orange-500 via-amber-600 to-yellow-700",
    red: "from-red-500 via-rose-600 to-pink-700"
  };

  const shadowColors = {
    blue: "hover:shadow-blue-500/50",
    purple: "hover:shadow-purple-500/50",
    green: "hover:shadow-green-500/50",
    orange: "hover:shadow-orange-500/50",
    red: "hover:shadow-red-500/50"
  };

  const baseClasses = `relative bg-gradient-to-br ${colorClasses[color]} rounded-2xl text-white shadow-lg transition-all duration-300 focus:outline-none p-4 md:p-[18px]`;
  const interactiveClasses = clickable
    ? `${baseClasses} cursor-pointer hover:scale-[1.02] hover:shadow-2xl ${shadowColors[color]}`
    : baseClasses;

  const CardContent = () => (
    <>
      {weekBadge && (
        <div className="absolute top-3 right-3 px-1.5 py-0.5 rounded text-[10px] bg-black bg-opacity-20 backdrop-blur-sm" style={{ opacity: 0.6 }}>
          Week {weekBadge}
        </div>
      )}
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5 opacity-90" strokeWidth={1.5} />
        {trend && trend !== 'same' && (
          <div className={`flex items-center text-sm ${trend === 'up' ? 'text-green-200' : 'text-red-200'}`}>
            {trend === 'up' ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
          </div>
        )}
      </div>
      <div className={`font-semibold mb-1 font-sans leading-tight ${value?.length > 6 ? 'text-2xl' : 'text-[28px] md:text-[32px]'}`}>{value}</div>
      <div className="font-medium opacity-80 font-sans" style={{ fontSize: '13px' }}>{title}</div>
      {subtitle && <div className="opacity-70 mt-1 font-sans" style={{ fontSize: '11px' }}>{subtitle}</div>}
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

  // Get ring color based on position
  const getRingColor = (tier) => {
    if (tier === 1) return '#FFD700'; // gold
    if (tier === 2) return '#C0C0C0'; // silver
    if (tier === 3) return '#CD7F32'; // bronze
    return undefined; // no ring for 4+
  };

  return (
    <div className={`flex items-center justify-between p-3 rounded-lg ${entry.isCurrentUser ? 'bg-purple-500/20 border border-purple-500/30' : ''}`}>
      <div className="flex items-center space-x-3">
        <UserAvatar
          username={entry.username}
          first_name={entry.first_name}
          last_name={entry.last_name}
          profilePicture={entry.avatar}
          size="sm"
          className="w-8 h-8 flex-shrink-0"
          ringColor={getRingColor(medalTier)}
        />
        <div className="flex items-center justify-center">{renderRankBadge(medalTier)}</div>
        <div>
          <div className={`font-medium text-sm ${entry.isCurrentUser ? 'text-purple-300' : 'text-white'} select-none`}>
            {capitalizeFirstLetter(entry.first_name || entry.username)}
          </div>
          <div className="text-xs select-none" style={{ color: '#9ca3af' }}>{entry.total_points ?? entry.points ?? 0} points</div>
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
  // Disabled useDashboardData - HomePage fetches its own data directly
  const [error, setError] = useState(null);
  const dashboardData = { user_data: {} };

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
  const [seasonPerf, setSeasonPerf] = useState({
    overall: 0,
    ml: 0,
    prop: 0,
    totalPoints: 0,
    loaded: false,
    propCategories: {}
  });

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

  // Build a medal/rank list for helpers, preserving trend
  const standingsForMedals = useMemo(() => {
    const sorted = [...standings].sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0));
    return sorted.map(s => ({ username: s.username, total_points: s.total_points }));
  }, [standings]);

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

        // season performance data
        setSeasonPerf({
          overall: Number((acc?.overallAccuracy ?? 0) * 100),
          ml: Number((acc?.moneylineAccuracy ?? 0) * 100),
          prop: Number((acc?.propBetAccuracy ?? 0) * 100),
          totalPoints: Number(acc?.totalPoints ?? 0),
          loaded: true,
          propCategories: acc?.propCategories || {}
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
                first_name: r.first_name,
                last_name: r.last_name,
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
                first_name: r.first_name,
                last_name: r.last_name,
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
      <div className="pt-16 sm:pt-[72px]">
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

  const goToWeeks = () => {
    navigate('/weeks');
  };

  // Prefer our local overlay; fall back to hook data if needed (keeps JSX unchanged)
  const userData = homeUserData || dashboardData?.user_data || {};

  return (
    <PageLayout>
      <div className="max-w-[1280px] mx-auto">
        {/* Header */}
        <div style={{ marginBottom: '16px' }} className="text-center md:text-left">
          <h1 className="font-bebas text-3xl sm:text-4xl font-bold tracking-wider uppercase">
            Welcome back, <span style={{
              background: 'linear-gradient(to right, #FF1CF7, #b249f8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>{userInfo.first_name || userInfo.username}</span>!
          </h1>
        </div>

        {/* Season Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" style={{ marginBottom: '16px' }}>
        <StatCard title="Current Rank" value={`#${userData.rank ?? '—'}`} subtitle={userData.currentWeek >= 2 && rankMeta.rankChange !== 0 ? `${rankMeta.rankChange > 0 ? '+' : ''}${rankMeta.rankChange} this week` : ""} icon={Trophy} trend={userData.currentWeek >= 2 ? rankMeta.trend : 'same'} color="green" />
        <StatCard
          title="Pending Picks"
          value={userData.pendingPicks ?? '—'}
          subtitle=""
          icon={Clock}
          color="purple"
          clickable={true}
          onClick={() => navigate(`/week/${userData.currentWeek}`)}
          weekBadge={userData.currentWeek}
        />
        <StatCard
          title="Points Behind 1st"
          value={userData.pointsFromLeader ?? '—'}
          subtitle=""
          icon={Footprints}
          color="orange"
          clickable={true}
          onClick={() => navigate('/standings')}
        />
        <StatCard
          title="Best Category"
          value={!seasonPerf.loaded ? '—' : (
            userData.bestCategory === 'Moneyline' ? '$-Line' :
            userData.bestCategory === 'PropBet' ? 'Prop Bet' :
            userData.bestCategory === 'Prop Bets' ? 'Prop Bets' :
            userData.bestCategory === 'Point Spread' ? 'Point Spread' :
            userData.bestCategory || 'N/A'
          )}
          subtitle={!seasonPerf.loaded ? '—' : `${userData.bestCategoryAccuracy || 0}% accuracy`}
          icon={ThumbsUp}
          color="blue"
        />
      </div>

        {/* Leaderboard + Season Performance */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 homepage-grid-equal-height">
        {/* Leaderboard (with trend arrows) */}
        <div className="homepage-glass-section p-4">
          <div className="homepage-glass-content">
            <div className="flex items-center justify-between">
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
            <button className="w-full mt-3 text-base sm:text-sm font-medium transition-colors homepage-section-content focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-opacity-50 rounded-md py-1" style={{ color: '#F59E0B', opacity: 0.75, letterSpacing: '0.05rem' }} onMouseEnter={(e) => e.target.style.color = '#FBBF24'} onMouseLeave={(e) => e.target.style.color = '#F59E0B'} onClick={() => navigate('/standings')}>
              View Full Standings →
            </button>
          </div>
        </div>

        {/* Season Performance */}
        <div className="homepage-glass-section season-performance-glass p-4">
          <div className="homepage-glass-content h-full flex flex-col">
            <h3 className="homepage-section-title mb-3">Season Performance</h3>
            <div className="flex-1 flex flex-col justify-center space-y-2.5">
              <PerformanceBar
                label="Moneyline"
                percentage={seasonPerf.ml || 0}
                color="#10B981"
              />
              <PerformanceBar
                label="Point Spread"
                percentage={(seasonPerf.propCategories?.point_spread?.accuracy || 0) * 100}
                color="#3B82F6"
              />
              <PerformanceBar
                label="Over/Under"
                percentage={(seasonPerf.propCategories?.over_under?.accuracy || 0) * 100}
                color="#F59E0B"
              />
              <PerformanceBar
                label="Take-the-Bait"
                percentage={(seasonPerf.propCategories?.take_the_bait?.accuracy || 0) * 100}
                color="#EF4444"
              />
              <PerformanceBar
                label="Overall"
                percentage={seasonPerf.overall || 0}
                color="#8B5CF6"
              />
            </div>
            <div className="mt-3 pt-3 border-t border-gray-700">
              <div className="flex items-center justify-between">
                <div className="text-xs font-medium opacity-70">Total Points</div>
                <div className="text-lg font-bold" style={{ color: "#F9A825" }}>
                  {seasonPerf.totalPoints || 0}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Games */}
        <div className="homepage-glass-section p-4">
          <div className="homepage-glass-content">
            <div className="flex items-center justify-between">
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
                const badgeBg = isGreen ? 'bg-green-500/20' : isYellow ? 'bg-yellow-500/20' : 'bg-red-500/20';
                const badgeText = isGreen ? 'text-green-300' : isYellow ? 'text-yellow-300' : 'text-red-300';
                const badge = isGreen ? '✓' : isYellow ? '◐' : '✗';

                return (
                  <div key={game.id} className={`p-3 rounded-lg border-l-4 transition-all duration-200 ${borderColor}`} style={{ backgroundColor: 'rgba(42, 42, 42, 0.5)' }}>
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

        {/* View Weeks Button */}
        <div className="flex justify-center" style={{ marginTop: '24px', paddingBottom: 'calc(100px + env(safe-area-inset-bottom, 0px))' }}>
          <button
            className="homepage-glass-button px-8 py-4 text-white transition-all duration-300 ease-out inline-flex items-center space-x-3 focus:outline-none font-roboto font-semibold"
            style={{ letterSpacing: '0.1rem' }}
            onClick={goToWeeks}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="transition-transform duration-300">
              <ellipse cx="12" cy="12" rx="6" ry="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M12 3v18M5.5 7.5l13 0M5.5 16.5l13 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span className="text-sm uppercase">View Weeks</span>
          </button>
        </div>
      </div>
    </PageLayout>
  );
}

export default HomePage;
