/**
 * Dashboard Page - Admin overview and statistics
 */
import React, { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { OverviewStats, DailyGameStats, LeaderboardEntry, SystemStatus } from '../../types/auth';

const DashboardPage: React.FC = () => {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyGameStats[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(() => {
      loadSystemStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const [overviewData, dailyData, leaderboardData, statusData] = await Promise.all([
        adminApi.getOverviewStats(),
        adminApi.getDailyGameStats(7),
        adminApi.getLeaderboard(5),
        adminApi.getSystemStatus(),
      ]);
      setOverview(overviewData);
      setDailyStats(dailyData);
      setLeaderboard(leaderboardData);
      setSystemStatus(statusData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const status = await adminApi.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      // Silently fail for status updates
    }
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">System overview and statistics</p>
      </div>

      {/* Overview Stats */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Total Users</p>
            <p className="text-2xl font-bold text-white">{overview.total_users}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Active Users</p>
            <p className="text-2xl font-bold text-green-400">{overview.active_users}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Total Games</p>
            <p className="text-2xl font-bold text-white">{overview.total_games}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Games Today</p>
            <p className="text-2xl font-bold text-blue-400">{overview.games_today}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Total Hands</p>
            <p className="text-2xl font-bold text-white">{overview.total_hands_played}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Active AI Agents</p>
            <p className="text-2xl font-bold text-purple-400">{overview.active_ai_agents}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        {systemStatus && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">System Status</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">CPU Usage</span>
                  <span className="text-white">{systemStatus.cpu_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      systemStatus.cpu_percent > 80 ? 'bg-red-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${systemStatus.cpu_percent}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Memory Usage</span>
                  <span className="text-white">{systemStatus.memory_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      systemStatus.memory_percent > 80 ? 'bg-red-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${systemStatus.memory_percent}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Disk Usage</span>
                  <span className="text-white">{systemStatus.disk_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      systemStatus.disk_percent > 90 ? 'bg-red-500' : 'bg-purple-500'
                    }`}
                    style={{ width: `${systemStatus.disk_percent}%` }}
                  ></div>
                </div>
              </div>
              <div className="pt-4 border-t border-gray-700 grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-gray-400 text-sm">Active Games</p>
                  <p className="text-xl font-bold text-white">{systemStatus.active_games}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Connections</p>
                  <p className="text-xl font-bold text-white">{systemStatus.active_connections}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Uptime</p>
                  <p className="text-xl font-bold text-white">{formatUptime(systemStatus.uptime_seconds)}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Leaderboard */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Top Players</h2>
          {leaderboard.length > 0 ? (
            <div className="space-y-3">
              {leaderboard.map((entry, idx) => (
                <div
                  key={entry.user_id}
                  className="flex items-center gap-4 p-3 bg-gray-700/50 rounded-lg"
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                      idx === 0
                        ? 'bg-yellow-500 text-black'
                        : idx === 1
                        ? 'bg-gray-400 text-black'
                        : idx === 2
                        ? 'bg-amber-600 text-black'
                        : 'bg-gray-600 text-white'
                    }`}
                  >
                    {entry.rank}
                  </div>
                  <div className="flex-1">
                    <p className="text-white font-medium">{entry.username}</p>
                    <p className="text-gray-400 text-sm">{entry.total_games} games</p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 font-bold">
                      +{entry.total_chips_won.toLocaleString()}
                    </p>
                    <p className="text-gray-400 text-sm">
                      {(entry.win_rate * 100).toFixed(1)}% WR
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400">No players yet</p>
          )}
        </div>

        {/* Daily Games Chart (simplified as a table) */}
        <div className="bg-gray-800 rounded-xl p-6 lg:col-span-2">
          <h2 className="text-xl font-bold text-white mb-4">Recent Activity (7 Days)</h2>
          {dailyStats.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Date</th>
                    <th className="text-right py-3 px-4 text-gray-400 font-medium">Games</th>
                    <th className="text-right py-3 px-4 text-gray-400 font-medium">Hands</th>
                    <th className="text-right py-3 px-4 text-gray-400 font-medium">Players</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyStats.map((day) => (
                    <tr key={day.date} className="border-b border-gray-700/50">
                      <td className="py-3 px-4 text-white">{day.date}</td>
                      <td className="py-3 px-4 text-right text-white">{day.games_count}</td>
                      <td className="py-3 px-4 text-right text-white">{day.hands_count}</td>
                      <td className="py-3 px-4 text-right text-white">{day.unique_players}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-400">No activity in the last 7 days</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
