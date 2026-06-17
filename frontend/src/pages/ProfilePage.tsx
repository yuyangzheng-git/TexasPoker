/**
 * Profile Page - User profile and statistics
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout, fetchUserStats } from '../store/authSlice';
import { authApi } from '../services/api';
import { AppDispatch, RootState } from '../store';
import { PasswordChangeRequest, UserUpdateRequest } from '../types/auth';

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { user, stats, isAuthenticated } = useSelector(
    (state: RootState) => state.auth
  );

  const [isEditing, setIsEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [editUsername, setEditUsername] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    dispatch(fetchUserStats());
  }, [isAuthenticated, navigate, dispatch]);

  useEffect(() => {
    if (user) {
      setEditUsername(user.username);
      setEditEmail(user.email);
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsLoading(true);

    try {
      const updateData: UserUpdateRequest = {};
      if (editUsername !== user?.username) updateData.username = editUsername;
      if (editEmail !== user?.email) updateData.email = editEmail;

      if (Object.keys(updateData).length === 0) {
        setIsEditing(false);
        setIsLoading(false);
        return;
      }

      await authApi.updateMe(updateData);
      dispatch(fetchUserStats());
      setSuccess('Profile updated successfully');
      setIsEditing(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setIsLoading(true);

    try {
      const data: PasswordChangeRequest = {
        old_password: oldPassword,
        new_password: newPassword,
      };
      await authApi.changePassword(data);
      setSuccess('Password changed successfully');
      setIsChangingPassword(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Profile</h1>
            <p className="text-gray-400 mt-1">Manage your account and view statistics</p>
          </div>
          <div className="flex gap-4">
            <Link
              to="/"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Back to Lobby
            </Link>
            {user.role !== 'user' && (
              <Link
                to="/admin"
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-500/20 border border-green-500 text-green-400 px-4 py-3 rounded-lg mb-6">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Profile Info */}
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Account Information</h2>
              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  Edit
                </button>
              )}
            </div>

            {isEditing ? (
              <form onSubmit={handleUpdateProfile} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={editUsername}
                    onChange={(e) => setEditUsername(e.target.value)}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg transition-colors"
                  >
                    {isLoading ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="text-gray-400 text-sm">Username</p>
                  <p className="text-white text-lg">{user.username}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Email</p>
                  <p className="text-white text-lg">{user.email}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Role</p>
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-sm ${
                      user.role === 'super_admin'
                        ? 'bg-purple-500/20 text-purple-400'
                        : user.role === 'admin'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}
                  >
                    {user.role}
                  </span>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Member Since</p>
                  <p className="text-white">
                    {new Date(user.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Password Change */}
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Security</h2>
            </div>

            {isChangingPassword ? (
              <form onSubmit={handleChangePassword} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg transition-colors"
                  >
                    {isLoading ? 'Changing...' : 'Change Password'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsChangingPassword(false)}
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button
                onClick={() => setIsChangingPassword(true)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Change Password
              </button>
            )}
          </div>

          {/* Statistics */}
          <div className="bg-gray-800 rounded-xl p-6 lg:col-span-2">
            <h2 className="text-xl font-bold text-white mb-6">Game Statistics</h2>

            {stats ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total Games</p>
                  <p className="text-2xl font-bold text-white">{stats.total_games}</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total Hands</p>
                  <p className="text-2xl font-bold text-white">{stats.total_hands}</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Win Rate</p>
                  <p className="text-2xl font-bold text-green-400">
                    {(stats.win_rate * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">W/L Record</p>
                  <p className="text-2xl font-bold text-white">
                    <span className="text-green-400">{stats.wins}</span>
                    <span className="text-gray-500 mx-1">/</span>
                    <span className="text-red-400">{stats.losses}</span>
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Chips Won</p>
                  <p className="text-2xl font-bold text-green-400">
                    +{stats.total_chips_won.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Chips Lost</p>
                  <p className="text-2xl font-bold text-red-400">
                    -{stats.total_chips_lost.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Biggest Pot Won</p>
                  <p className="text-2xl font-bold text-yellow-400">
                    {stats.biggest_pot_won.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">VPIP / PFR</p>
                  <p className="text-2xl font-bold text-white">
                    {(stats.vpip * 100).toFixed(0)}% / {(stats.pfr * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-400">No statistics available yet. Play some games!</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
