/*
 * Enhanced HomePage Component with Real Database Integration
 * Now uses actual database data instead of mock data
 * REFACTORED: Using PageLayout for consistent navbar alignment
 * ENHANCED: Added skeleton loaders for user stats section
 */

import React, { useState, useEffect } from 'react';
import { useAuthWithNavigation } from '../hooks/useAuthWithNavigation';
import useDashboardData from '../hooks/useDashboardData';
import PageLayout from '../components/common/PageLayout';
import { TrendingUp, TrendingDown, Trophy, Target, Clock, Users, Zap } from 'lucide-react';
import confetti from 'canvas-confetti';

// Skeleton Components
const StatCardSkeleton = () => (
  <div className="bg-gradient-to-br from-gray-600 to-gray-700 rounded-2xl p-6 shadow-lg animate-pulse">
    <div className="flex items-center justify-between">
      <div className="w-8 h-8 bg-gray-500 rounded opacity-50"></div>
    </div>
    <div className="w-16 h-8 bg-gray-500 rounded mt-4 mb-1"></div>
    <div className="w-20 h-4 bg-gray-500 rounded opacity-70"></div>
  </div>
);

const ProgressRingSkeleton = ({ size = 80 }) => (
  <div className="flex flex-col items-center">
    <div 
      className="rounded-full bg-gray-600 animate-pulse flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <div className="w-6 h-6 bg-gray-500 rounded"></div>
    </div>
    <div className="mt-2 w-12 h-3 bg-gray-600 rounded animate-pulse"></div>
  </div>
);

const SeasonPerformanceSkeleton = () => (
  <div className="rounded-2xl p-4 flex flex-col items-center justify-center mb-6">
    <div className="w-32 h-5 bg-gray-600 rounded mb-4 animate-pulse"></div>
    
    <div className="flex space-x-4 items-center">
      <ProgressRingSkeleton size={80} />
      <ProgressRingSkeleton size={80} />
      <ProgressRingSkeleton size={80} />
    </div>
    
    <div className="mt-4 text-center">
      <div className="w-16 h-6 bg-gray-600 rounded mb-1 animate-pulse mx-auto"></div>
      <div className="w-20 h-3 bg-gray-600 rounded animate-pulse mx-auto"></div>
    </div>
  </div>
);

// Component definitions remain the same
const ProgressRing = ({ percentage, size = 120, strokeWidth = 8, showPercentage = true, fontSize = 'text-2xl' }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = `${circumference} ${circumference}`;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        className="transform -rotate-90"
        width={size}
        height={size}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(139, 92, 246, 0.1)"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#gradient)"
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8B5CF6" />
            <stop offset="100%" stopColor="#7C3AED" />
          </linearGradient>
        </defs>
      </svg>
      {showPercentage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-bold text-white ${fontSize}`}>{Math.round(percentage)}%</span>
        </div>
      )}
    </div>
  );
};

const StatCard = ({ title, value, subtitle, icon: Icon, trend, color = "blue", animated = false }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const colorClasses = {
    blue: "from-blue-500 to-blue-600",
    purple: "from-purple-500 to-purple-600", 
    green: "from-green-500 to-green-600",
    orange: "from-orange-500 to-orange-600",
    red: "from-red-500 to-red-600"
  };

  return (
    <div className={`
      bg-gradient-to-br ${colorClasses[color]} 
      rounded-2xl p-6 text-white shadow-lg hover:shadow-xl 
      transition-all duration-300 hover:scale-105 cursor-pointer
      ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
    `}>
      <div className="flex items-center justify-between">
        <Icon className="w-8 h-8 opacity-80" />
        {trend && trend !== 'same' && (
          <div className={`flex items-center text-sm ${trend === 'up' ? 'text-green-200' : 'text-red-200'}`}>
            {trend === 'up' ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
          </div>
        )}
      </div>
      <div className={`text-3xl font-bold mb-1 ${animated ? 'transition-all duration-1000' : ''}`}>
        {value}
      </div>
      <div className="text-sm opacity-90">{title}</div>
      {subtitle && <div className="text-xs opacity-70 mt-1">{subtitle}</div>}
    </div>
  );
};

const RecentGameCard = ({ game }) => {
  return (
    <div className={`
      p-4 rounded-lg border-l-4 transition-all duration-200
      ${game.correct ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'}
    `}
    style={{ backgroundColor: game.correct ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="text-sm font-medium" style={{ color: '#9ca3af' }}>
            {game.awayTeam} @ {game.homeTeam}
          </div>
          <div className={`text-xs px-2 py-1 rounded-full ${
            game.correct ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
          }`}>
            {game.correct ? '✓' : '✗'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-white">+{game.points} pts</div>
          <div className="text-xs" style={{ color: '#9ca3af' }}>Pick: {game.userPick}</div>
        </div>
      </div>
    </div>
  );
};

const LeaderboardRow = ({ user, index }) => {
  return (
    <div className={`
      flex items-center justify-between p-3 rounded-lg transition-all duration-200
      ${user.isCurrentUser ? 'bg-purple-500/20 border border-purple-500/30' : 'hover:bg-gray-700/50'}
    `}>
      <div className="flex items-center space-x-3">
        <div className={`
          w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
          ${index < 3 ? 'bg-yellow-500 text-yellow-900' : 'bg-gray-600 text-white'}
        `}>
          {user.rank}
        </div>
        <div>
          <div className={`font-medium ${user.isCurrentUser ? 'text-purple-300' : 'text-white'}`}>
            {user.username}
          </div>
          <div className="text-xs" style={{ color: '#9ca3af' }}>{user.points} points</div>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        {user.trend === 'up' && <TrendingUp className="w-4 h-4 text-green-400" />}
        {user.trend === 'down' && <TrendingDown className="w-4 h-4 text-red-400" />}
      </div>
    </div>
  );
};

const LoadingSpinner = () => (
  <div className="flex items-center justify-center py-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
  </div>
);

function HomePage() {
  const { userInfo, navigate } = useAuthWithNavigation();
  const { dashboardData, loadingStates, error } = useDashboardData(userInfo, {
    loadGranular: true,
    includeLeaderboard: true,
  });
  const [animatedStats, setAnimatedStats] = useState(false);

  useEffect(() => {
    if (userInfo && dashboardData) {
      const timer = setTimeout(() => setAnimatedStats(true), 300);
      return () => clearTimeout(timer);
    }
  }, [userInfo, dashboardData]);

  const handleConfetti = () => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
    navigate('/weeks');
  };

  // Not logged in - use basic container (no PageLayout needed for auth pages)
  if (!userInfo) {
    return (
      <div className="pt-16">
        <h2>you are not logged in</h2>
        <p className="text-center text-small">
          <a href="/login" style={{ color: '#8B5CF6', fontSize: '16px' }}>
            Login
          </a>
        </p>
        <p className="text-center text-small">
          <a href="/signup" style={{ color: '#8B5CF6', fontSize: '16px' }}>
            Sign Up
          </a>
        </p>
      </div>
    );
  }

  // Error state with PageLayout
  if (error) {
    return (
      <PageLayout>
        <div className="text-center py-8">
          <p className="text-red-400">Error loading dashboard: {error}</p>
          <button 
            className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </PageLayout>
    );
  }

  // Extract data from API response - FIXED to match current hook structure
  const userData = dashboardData?.user_data || {};
  const leaderboard = dashboardData?.leaderboard || [];
  const insights = dashboardData?.insights || [];
  const recentGames = userData.recentGames || [];

  return (
    <PageLayout>
      {/* Welcome Header */}
      <div className="mb-6 text-center">
        <h2 className="text-2xl sm:text-3xl font-bold mb-2">
          Welcome back, <span style={{ color: '#8B5CF6' }}>{userInfo.username}</span>!
        </h2>
        <p style={{ color: '#9ca3af', fontSize: '14px' }}>
          Week {userData.currentWeek} • Ready to make your picks?
        </p>
      </div>

      {/* Quick Stats Grid - WITH SKELETONS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {loadingStates.stats ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Current Rank"
              value={`#${userData.rank || '—'}`}
              subtitle={`${userData.rankChange || ''} this week`}
              icon={Trophy}
              trend={userData.rankTrend || null}
              color="purple"
            />

            <StatCard
              title="Pending Picks"
              value={userData.pendingPicks || 0}
              subtitle="for this week"
              icon={Clock}
              color="blue"
            />
        
            <StatCard
              title="Points Behind"
              value={userData.pointsFromLeader || 0}
              subtitle="from 1st place"
              icon={Target}
              color="orange"
            />

            <StatCard
              title="Best Category"
              value={userData.bestCategory === 'Moneyline' ? '$-line' : userData.bestCategory || 'N/A'}
              subtitle={`${userData.bestCategoryAccuracy || 0}% accuracy`}
              icon={Zap}
              color="green"
            />
          </>
        )}
      </div>

      {/* Season Performance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {/* Season Performance Card - WITH SKELETON */}
        {loadingStates.accuracy ? (
          <SeasonPerformanceSkeleton />
        ) : (
          <div className="rounded-2xl p-4 flex flex-col items-center justify-center mb-6">
            <h3 className="text-lg font-semibold mb-4">Season Performance</h3>
            
            {/* All Three Progress Rings Side by Side */}
            <div className="flex space-x-4 items-center">
              <div className="flex flex-col items-center">
                <ProgressRing 
                  percentage={userData.overallAccuracy || 0} 
                  size={80} 
                  strokeWidth={6} 
                  fontSize="text-base" 
                />
                <div className="mt-2 text-center">
                  <div className="text-xs font-bold" style={{ color: '#F9A825' }}>Overall</div>
                </div>
              </div>
              
              <div className="flex flex-col items-center">
                <ProgressRing 
                  percentage={userData.moneylineAccuracy || 0} 
                  size={80} 
                  strokeWidth={6} 
                  showPercentage={true} 
                  fontSize="text-base" 
                />
                <div className="mt-2 text-center">
                  <div className="text-xs font-bold text-green-400">Moneyline</div>
                </div>
              </div>
              
              <div className="flex flex-col items-center">
                <ProgressRing 
                  percentage={userData.propBetAccuracy || 0} 
                  size={80} 
                  strokeWidth={6} 
                  showPercentage={true} 
                  fontSize="text-base"
                />
                <div className="mt-2 text-center">
                  <div className="text-xs font-bold text-blue-400">Prop Bets</div>
                </div>
              </div>
            </div>
            
            <div className="mt-4 text-center">
              <div className="text-2xl font-bold" style={{ color: "#F9A825" }}>
                {userData.totalPoints || 0}
              </div>
              <div className="text-sm" style={{ color: '#9ca3af' }}>Total Points</div>
            </div>
          </div>
        )}
        
        {/* Leaderboard */}
        <div className="rounded-2xl p-4 mb-6" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Leaderboard</h3>
            <Users className="w-4 h-4" style={{ color: '#9ca3af' }} />
          </div>
          <div className="space-y-2">
            {loadingStates.leaderboard ? (
              <LoadingSpinner />
            ) : (
              <>
                {leaderboard.slice(0, 3).map((user, index) => (
                  <LeaderboardRow key={user.rank || index} user={user} index={index} />
                ))}
              </>
            )}
          </div>
          <button 
            className="w-full mt-3 text-xs font-medium transition-colors hover:text-purple-300"
            style={{ color: '#8B5CF6' }}
            onClick={() => navigate('/standings')}
          >
            View Full Standings →
          </button>
        </div>

        {/* Recent Activity */}
        <div className="rounded-2xl p-4 mb-6" style={{ backgroundColor: '#2d2d2d' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Recent Games</h3>
            <Clock className="w-4 h-4" style={{ color: '#9ca3af' }} />
          </div>
          <div className="space-y-3">
            {loadingStates.recent ? (
              <LoadingSpinner />
            ) : (
              <>  
                {recentGames.length > 0 ? (
                  recentGames.slice(0, 2).map(game => (
                    <RecentGameCard key={game.id} game={game} />
                  ))
                ) : (
                  <div className="text-center py-4" style={{ color: '#9ca3af' }}>
                    <p>No recent completed games</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Insights Section */}
      {insights.length > 0 && (
        <div className="rounded-2xl p-4 mb-6" style={{ backgroundColor: '#1f1f1f' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Insights</h3>
            <Zap className="w-4 h-4" style={{ color: '#9ca3af' }} />
          </div>
          <div className="space-y-3">
            {loadingStates.insights ? (
              <LoadingSpinner />
            ) : (
              <>
                {insights.map((insight, index) => (
                  <div 
                    key={index}
                    className={`p-3 rounded-lg border-l-4 ${
                      insight.type === 'positive' ? 'border-green-500 bg-green-500/10' :
                      insight.type === 'warning' ? 'border-yellow-500 bg-yellow-500/10' :
                      'border-blue-500 bg-blue-500/10'
                    }`}
                  >
                    <p className="text-sm text-white">{insight.message}</p>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Action Button */}
      <div className="flex justify-center">
        <button 
          className="px-6 py-3 rounded-2xl text-white font-semibold text-base transition-all duration-200 hover:scale-105 shadow-lg inline-flex items-center space-x-2"
          style={{ background: 'linear-gradient(135deg, #8B5CF6, #7C3AED)' }}
          onClick={handleConfetti}
        >
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
