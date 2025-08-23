import { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import PageLayout from '../components/common/PageLayout';
import { Trophy, TrendingUp, TrendingDown, Crown, Medal, Award } from 'lucide-react';

export default function Standings() {
  const { userInfo } = useAuth();
  const [standings, setStandings] = useState([]);
  const [weeks, setWeeks] = useState([]);
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef(null);

  const API_BASE = import.meta.env.VITE_API_URL;

  useEffect(() => {
    const fetchStandings = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/predictions/api/standings/`, {
          credentials: 'include',
        });
        const data = await res.json();
        setStandings(data.standings);
        setWeeks(data.weeks.sort((a, b) => a - b));
      } catch (err) {
        console.error('Failed to load standings:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStandings();
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

  const sortedStandings = [...standings].sort((a, b) => {
    const aPoints = selectedWeek ? a.weekly_scores[selectedWeek] || 0 : a.total_points;
    const bPoints = selectedWeek ? b.weekly_scores[selectedWeek] || 0 : b.total_points;

    if (bPoints !== aPoints) return bPoints - aPoints;
    return a.username.localeCompare(b.username);
  });

  const getRankIcon = (rank) => {
    switch (rank) {
      case 1:
        return <Crown className="w-5 h-5 text-yellow-500" />;
      case 2:
        return <Medal className="w-5 h-5 text-gray-400" />;
      case 3:
        return <Award className="w-5 h-5 text-amber-600" />;
      default:
        return <Trophy className="w-5 h-5 text-gray-500" />;
    }
  };

  const getRankBadgeColor = (rank) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-yellow-900';
      case 2:
        return 'bg-gradient-to-r from-gray-300 to-gray-500 text-gray-900';
      case 3:
        return 'bg-gradient-to-r from-amber-400 to-amber-600 text-amber-900';
      default:
        return 'bg-gradient-to-r from-gray-600 to-gray-700 text-white';
    }
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
      {/* Header Section */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-2 font-bebas">
          League Standings
        </h1>
        <p className="text-gray-400">
          {selectedWeek ? `Week ${selectedWeek} Results` : 'Season Leaderboard'}
        </p>
      </div>

      {/* Week Filter Dropdown */}
      <div className="flex justify-center mb-8">
        <div className="relative inline-block text-left" ref={dropdownRef}>
          <button
            onClick={() => setOpen(!open)}
            className="inline-flex items-center justify-between w-64 px-6 py-3 text-sm font-medium rounded-xl shadow-lg focus:outline-none text-white hover:bg-gray-700 transition-all duration-200 border border-gray-600"
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
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.293l3.71-4.06a.75.75 0 111.08 1.04l-4.25 4.65a.75.75 0 01-1.08 0l-4.25-4.65a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </button>

          {open && (
            <div className="absolute z-10 mt-2 w-64 rounded-xl shadow-2xl border border-gray-600 overflow-hidden" style={{ backgroundColor: '#2d2d2d' }}>
              <ul className="py-2">
                <li>
                  <button
                    onClick={() => {
                      setSelectedWeek(null);
                      setOpen(false);
                    }}
                    className="w-full px-6 py-3 text-left text-white hover:bg-gray-700 transition-colors duration-150 flex items-center"
                  >
                    <Trophy className="w-4 h-4 mr-3" />
                    All Weeks (Total)
                  </button>
                </li>
                {weeks.map((week) => (
                  <li key={week}>
                    <button
                      onClick={() => {
                        setSelectedWeek(week);
                        setOpen(false);
                      }}
                      className="w-full px-6 py-3 text-left text-white hover:bg-gray-700 transition-colors duration-150 flex items-center"
                    >
                      <Award className="w-4 h-4 mr-3" />
                      Week {week}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Standings Cards */}
      <div className="space-y-4">
        {sortedStandings.length === 0 ? (
          <div className="text-center py-16">
            <Trophy className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-400 mb-2">No standings available</h3>
            <p className="text-gray-500">Check back later for results!</p>
          </div>
        ) : (
          sortedStandings.map((entry, index) => {
            const rank = index + 1;
            const points = selectedWeek
              ? entry.weekly_scores[selectedWeek] || 0
              : entry.total_points;
            const isCurrentUser = entry.username === userInfo?.username;

            return (
              <div
                key={entry.username}
                className={`
                  relative rounded-2xl p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl border
                  ${isCurrentUser 
                    ? 'bg-gradient-to-r from-purple-900/20 to-purple-800/20 border-purple-500/50 shadow-purple-500/20' 
                    : 'bg-gradient-to-r from-gray-800/50 to-gray-900/50 border-gray-700/50'
                  }
                `}
                style={{ 
                  backgroundColor: isCurrentUser ? 'rgba(139, 92, 246, 0.1)' : 'rgba(45, 45, 45, 0.8)',
                  boxShadow: isCurrentUser 
                    ? '0 20px 25px -5px rgba(139, 92, 246, 0.1), 0 10px 10px -5px rgba(139, 92, 246, 0.04)' 
                    : '0 10px 15px -3px rgba(0, 0, 0, 0.3)'
                }}
              >
                {/* Rank Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`
                      flex items-center justify-center w-12 h-12 rounded-xl font-bold text-lg
                      ${getRankBadgeColor(rank)}
                    `}>
                      {rank <= 3 ? getRankIcon(rank) : rank}
                    </div>
                    
                    <div>
                      <div className={`
                        font-bold text-lg
                        ${isCurrentUser ? 'text-purple-300' : 'text-white'}
                      `}>
                        {entry.username}
                        {isCurrentUser && (
                          <span className="ml-2 px-2 py-1 text-xs bg-purple-500 text-white rounded-full">
                            You
                          </span>
                        )}
                      </div>
                      <div className="text-gray-400 text-sm">
                        Rank #{rank}
                      </div>
                    </div>
                  </div>

                  {/* Points Display */}
                  <div className="text-right">
                    <div className="text-3xl font-bold text-white mb-1">
                      {points}
                    </div>
                    <div className="text-gray-400 text-sm">
                      {selectedWeek ? 'week points' : 'total points'}
                    </div>
                  </div>
                </div>

                {/* Trend Indicator (if available) */}
                {entry.trend && (
                  <div className="absolute top-4 right-4">
                    {entry.trend === 'up' && (
                      <TrendingUp className="w-5 h-5 text-green-400" />
                    )}
                    {entry.trend === 'down' && (
                      <TrendingDown className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                )}

                {/* Top 3 Special Effects */}
                {rank <= 3 && (
                  <div className="absolute inset-0 rounded-2xl opacity-20 pointer-events-none">
                    <div className={`
                      absolute inset-0 rounded-2xl
                      ${rank === 1 ? 'bg-gradient-to-r from-yellow-400/20 to-yellow-600/20' : ''}
                      ${rank === 2 ? 'bg-gradient-to-r from-gray-300/20 to-gray-500/20' : ''}
                      ${rank === 3 ? 'bg-gradient-to-r from-amber-400/20 to-amber-600/20' : ''}
                    `} />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Stats Summary */}
      {standings.length > 0 && (
        <div className="mt-12 text-center">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-r from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
              <Trophy className="w-8 h-8 text-yellow-500 mx-auto mb-3" />
              <div className="text-2xl font-bold text-white mb-1">
                {standings.length}
              </div>
              <div className="text-gray-400">Total Players</div>
            </div>
            
            <div className="bg-gradient-to-r from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
              <Crown className="w-8 h-8 text-purple-500 mx-auto mb-3" />
              <div className="text-2xl font-bold text-white mb-1">
                {sortedStandings[0]?.total_points || 0}
              </div>
              <div className="text-gray-400">Leading Score</div>
            </div>
            
            <div className="bg-gradient-to-r from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50">
              <Award className="w-8 h-8 text-green-500 mx-auto mb-3" />
              <div className="text-2xl font-bold text-white mb-1">
                {weeks.length}
              </div>
              <div className="text-gray-400">Weeks Tracked</div>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}