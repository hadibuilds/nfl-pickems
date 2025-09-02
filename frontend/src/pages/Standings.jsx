import { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import PageLayout from '../components/common/PageLayout';
import UserAvatar from '../components/common/UserAvatar';
import { Trophy, Award, TrendingUp, TrendingDown } from 'lucide-react';
import {
  sortStandings,
  calculateRankWithTies,
  getMedalTier,
  getRingColorClass,
  capitalizeFirstLetter,
  renderRank
} from '../components/standings/rankingUtils.jsx';

export default function Standings() {
  const { userInfo } = useAuth();
  const [standings, setStandings] = useState([]);
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [weeks, setWeeks] = useState([]);
  const [currentWeek, setCurrentWeek] = useState(null);    // ← authoritative current week
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef(null);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        // Fetch both standings and leaderboard data in parallel
        const [standingsRes, leaderboardRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/api/standings/`, { credentials: 'include' }),
          fetch(`${API_BASE}/analytics/api/leaderboard/?limit=100`, { credentials: 'include' })
        ]);
        
        if (!standingsRes.ok) throw new Error('Failed to load standings');
        const standingsData = await standingsRes.json();
        setStandings(Array.isArray(standingsData.standings) ? standingsData.standings : []);
        setWeeks(Array.isArray(standingsData.weeks) ? [...standingsData.weeks].sort((a, b) => a - b) : []);
        
        // Fetch leaderboard for trend data (season totals with rank_delta)
        if (leaderboardRes.ok) {
          const leaderboardData = await leaderboardRes.json();
          setLeaderboardData(Array.isArray(leaderboardData.leaderboard) ? leaderboardData.leaderboard : []);
        }
      } catch (err) {
        console.error('Failed to load standings:', err);
        setStandings([]);
        setLeaderboardData([]);
        setWeeks([]);
      } finally {
        setLoading(false);
      }
    };

    const fetchCurrentWeek = async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics/api/current-week/`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json(); // { currentWeek, weeks? }
        if (Number.isInteger(data.currentWeek)) {
          setCurrentWeek(data.currentWeek);
          // If selected week is in the future, reset it
          setSelectedWeek((prev) => (prev && prev > data.currentWeek ? null : prev));
        }
      } catch (e) {
        console.warn('current-week endpoint unavailable; falling back to data.weeks');
      }
    };

    fetchAll();
    fetchCurrentWeek();
  }, [API_BASE]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Only expose current & prior weeks in the dropdown
  const filteredWeeks = (() => {
    if (currentWeek == null) return weeks; // fallback if endpoint not available
    return weeks.filter((w) => w <= currentWeek);
  })().sort((a, b) => b - a); // show most recent first

  // Use leaderboard data for "All Weeks" view to get trends, otherwise use standings data
  const sortedStandings = selectedWeek === null && leaderboardData.length > 0 
    ? leaderboardData.sort((a, b) => b.total_points - a.total_points)
    : sortStandings(standings, selectedWeek);

  const getContainerStyling = (isCurrentUser) => {
    let base = 'rounded-xl p-4 transition-all duration-300 border ';
    return isCurrentUser
      ? base + 'bg-gradient-to-r from-purple-900/20 to-purple-800/20 border-purple-500/50'
      : base + 'bg-gradient-to-r from-gray-800/50 to-gray-900/50 border-gray-700/50';
  };

  const LoadingSpinner = () => (
    <div className="flex items-center justify-center py-16">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
    </div>
  );

  if (loading) {
    return (
      <PageLayout>
        <LoadingSpinner />
        <p className="text-center text-gray-400 mt-4">Loading standings...</p>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="text-center mb-6">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-2 font-bebas tracking-wider">League Standings</h1>
        <p className="text-gray-400">
          {selectedWeek ? `Week ${selectedWeek} Results` : 'Season Leaderboard'}
        </p>
      </div>

      {/* Week Filter */}
      <div className="flex justify-center mb-6">
        <div className="relative inline-block text-left" ref={dropdownRef}>
          <button
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center justify-between w-60 px-5 py-2.5 text-sm font-medium rounded-xl shadow-lg focus:outline-none text-white hover:bg-gray-700 transition-all duration-200 border border-gray-600"
            style={{ backgroundColor: '#2d2d2d' }}
          >
            <span className="flex items-center">
              <Trophy className="w-4 h-4 mr-2" />
              {selectedWeek ? `Week ${selectedWeek}` : 'All Weeks (Total)'}
            </span>
            <svg
              className={`w-4 h-4 ml-2 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M5.23 7.21a.75.75 0 011.06.02L10 11.293l3.71-4.06a.75.75 0 111.08 1.04l-4.25 4.65a.75.75 0 01-1.08 0l-4.25-4.65a.75.75 0 01.02-1.06z"
                clipRule="evenodd"
              />
            </svg>
          </button>

          {open && (
            <div
              className="absolute z-10 mt-2 w-60 rounded-xl shadow-2xl border border-gray-600 overflow-hidden"
              style={{ backgroundColor: '#2d2d2d' }}
            >
              <ul className="py-1">
                <li>
                  <button
                    onClick={() => { setSelectedWeek(null); setOpen(false); }}
                    className="w-full px-5 py-2.5 text-left text-white hover:bg-gray-700 transition-colors duration-150 flex items-center"
                  >
                    <Trophy className="w-4 h-4 mr-3" /> All Weeks (Total)
                  </button>
                </li>

                {/* SCROLLABLE list of weeks (only current & before) */}
                <li>
                  <div className="max-h-60 overflow-y-auto">
                    {filteredWeeks.map((week) => (
                      <button
                        key={week}
                        onClick={() => { setSelectedWeek(week); setOpen(false); }}
                        className="w-full px-5 py-2.5 text-left text-white hover:bg-gray-700 transition-colors duration-150 flex items-center"
                      >
                        <Award className="w-4 h-4 mr-3" /> Week {week}
                      </button>
                    ))}
                  </div>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Standings List — contained scrollbox */}
      <div className="max-w-md mx-auto">
        <div className="max-h-[70vh] overflow-y-auto space-y-3 pr-1">
          {sortedStandings.length === 0 ? (
            <div className="text-center py-16">
              <Trophy className="w-16 h-16 text-gray-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No standings available</h3>
              <p className="text-gray-500">Check back later for results!</p>
            </div>
          ) : (
            sortedStandings.map((entry, index) => {
              const points = selectedWeek
                ? (entry.weekly_scores?.[selectedWeek] ?? 0)
                : (entry.total_points ?? 0);
              const isCurrentUser = String(entry.username) === String(userInfo?.username);

              // Use leaderboard data for All Weeks view, standings data for specific weeks
              const isLeaderboardView = selectedWeek === null && leaderboardData.length > 0;
              const displayRank = isLeaderboardView 
                ? (entry.rank_dense || index + 1)
                : calculateRankWithTies(standings, entry.username, selectedWeek);
              const medalTier = isLeaderboardView
                ? (index < 3 ? ['gold', 'silver', 'bronze'][index] : null)
                : getMedalTier(standings, entry.username, selectedWeek);
              
              // Trend arrow logic for leaderboard view
              const rankDelta = isLeaderboardView ? (entry.rank_delta || 0) : 0;
              const showTrend = isLeaderboardView && rankDelta !== 0;
              const trendDirection = rankDelta > 0 ? 'up' : 'down';

              return (
                <div key={entry.username} className={getContainerStyling(isCurrentUser)}>
                  <div className="flex items-center space-x-4">
                    <UserAvatar
                      username={entry.username}
                      profilePicture={entry.avatar}
                      size="md"
                      className={`w-12 h-12 flex-shrink-0 ${getRingColorClass(medalTier)}`}
                    />
                    <div className="w-8 flex justify-center">
                      {renderRank(medalTier, displayRank)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`font-bold text-lg truncate ${isCurrentUser ? 'text-purple-300' : 'text-white'}`}>
                        {capitalizeFirstLetter(entry.first_name || entry.username)}
                      </div>
                    </div>
                    {showTrend && (
                      <div className={`flex items-center text-sm ${trendDirection === 'up' ? 'text-green-400' : 'text-red-400'}`}>
                        {trendDirection === 'up' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        <span className="ml-1">{Math.abs(rankDelta)}</span>
                      </div>
                    )}
                    <div className="text-2xl font-bold text-white">
                      {points}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </PageLayout>
  );
}
