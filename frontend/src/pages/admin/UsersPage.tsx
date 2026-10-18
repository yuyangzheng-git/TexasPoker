/**
 * Users Page - User management
 */
import React, { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { User, UserAdminUpdate } from '../../types/auth';

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editActive, setEditActive] = useState(true);

  useEffect(() => {
    loadUsers();
  }, [page, search, roleFilter, activeFilter]);

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const params: { page: number; page_size: number; search?: string; role?: string; is_active?: boolean } = {
        page,
        page_size: 20,
      };
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      if (activeFilter !== undefined) params.is_active = activeFilter;

      const data = await adminApi.listUsers(params);
      setUsers(data.users);
      setTotalUsers(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadUsers();
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setEditRole(user.role);
    setEditActive(user.is_active);
  };

  const handleSaveUser = async () => {
    if (!editingUser) return;

    try {
      const updateData: UserAdminUpdate = {};
      if (editRole !== editingUser.role) updateData.role = editRole;
      if (editActive !== editingUser.is_active) updateData.is_active = editActive;

      if (Object.keys(updateData).length === 0) {
        setEditingUser(null);
        return;
      }

      await adminApi.updateUser(editingUser.id, updateData);
      setEditingUser(null);
      loadUsers();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">成员管理</h1>
        <p className="text-gray-400 mt-1">查找成员、查看账户状态与管理权限</p>
      </div>

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
          <button onClick={() => setError(null)} className="float-right text-red-400 hover:text-red-300">
            &times;
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search username or email..."
            className="flex-1 min-w-[200px] px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">全部身份</option>
            <option value="user">成员</option>
            <option value="admin">管理员</option>
            <option value="super_admin">超级管理员</option>
          </select>
          <select
            value={activeFilter === undefined ? '' : activeFilter.toString()}
            onChange={(e) => {
              const val = e.target.value;
              setActiveFilter(val === '' ? undefined : val === 'true');
              setPage(1);
            }}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">全部状态</option>
            <option value="true">已启用</option>
            <option value="false">已停用</option>
          </select>
          <button
            type="submit"
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            搜索
          </button>
        </form>
      </div>

      {/* Users Table */}
      <div className="bg-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-700/50">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">ID</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">用户名</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">邮箱</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">身份</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">状态</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">加入时间</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">最近登录</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                      <td className="py-3 px-4 text-gray-400">{user.id}</td>
                      <td className="py-3 px-4 text-white font-medium">{user.username}</td>
                      <td className="py-3 px-4 text-gray-300">{user.email}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs ${
                            user.role === 'super_admin'
                              ? 'bg-purple-500/20 text-purple-400'
                              : user.role === 'admin'
                              ? 'bg-blue-500/20 text-blue-400'
                              : 'bg-gray-500/20 text-gray-400'
                          }`}
                        >
                          {user.role}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs ${
                            user.is_active
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm">
                        {user.last_login
                          ? new Date(user.last_login).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => handleEditUser(user)}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          编辑
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="p-4 border-t border-gray-700 flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                Showing {users.length} of {totalUsers} users
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition-colors"
                >
                  上一页
                </button>
                <span className="px-3 py-1 text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition-colors"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">
              Edit User: {editingUser.username}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  身份
                </label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="user">成员</option>
                  <option value="admin">管理员</option>
                  <option value="super_admin">超级管理员</option>
                </select>
              </div>
              <div>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editActive}
                    onChange={(e) => setEditActive(e.target.checked)}
                    className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-gray-300">启用账户</span>
                </label>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSaveUser}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                保存修改
              </button>
              <button
                onClick={() => setEditingUser(null)}
                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
