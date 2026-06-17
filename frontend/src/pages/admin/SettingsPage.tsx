/**
 * Settings Page - System configuration and monitoring
 */
import React, { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { SystemConfig, SystemConfigUpdate, AuditLog } from '../../types/auth';
import { useSelector } from 'react-redux';
import { RootState } from '../../store';

const SettingsPage: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(true);
  const [isLoadingLogs, setIsLoadingLogs] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [editValue, setEditValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'config' | 'audit'>('config');

  const isSuperAdmin = user?.role === 'super_admin';

  useEffect(() => {
    loadConfigs();
    loadAuditLogs();
  }, []);

  const loadConfigs = async () => {
    try {
      setIsLoadingConfigs(true);
      const data = await adminApi.listSystemConfigs();
      setConfigs(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoadingConfigs(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      setIsLoadingLogs(true);
      const data = await adminApi.listAuditLogs({ page: 1, page_size: 50 });
      setAuditLogs(data.logs);
    } catch (err) {
      // Non-fatal error for audit logs
      console.error('Failed to load audit logs:', err);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  const handleEditConfig = (config: SystemConfig) => {
    if (!isSuperAdmin) {
      setError('Only super admins can modify system configuration');
      return;
    }
    setEditingConfig(config);
    setEditValue(config.value || '');
  };

  const handleSaveConfig = async () => {
    if (!editingConfig) return;

    try {
      setIsSaving(true);
      const updateData: SystemConfigUpdate = {
        value: editValue,
      };
      await adminApi.updateSystemConfig(editingConfig.key, updateData);
      setEditingConfig(null);
      loadConfigs();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">System Settings</h1>
        <p className="text-gray-400 mt-1">Configure system parameters and view audit logs</p>
      </div>

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
          <button onClick={() => setError(null)} className="float-right text-red-400 hover:text-red-300">
            &times;
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('config')}
          className={`px-6 py-2 rounded-lg transition-colors ${
            activeTab === 'config'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          System Configuration
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-6 py-2 rounded-lg transition-colors ${
            activeTab === 'audit'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Audit Logs
        </button>
      </div>

      {/* System Configuration Tab */}
      {activeTab === 'config' && (
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          {!isSuperAdmin && (
            <div className="bg-yellow-500/20 border-b border-yellow-500 text-yellow-400 px-4 py-3">
              Only super administrators can modify system configuration.
            </div>
          )}

          {isLoadingConfigs ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
            </div>
          ) : configs.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-700/50">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Key</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Value</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Type</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Description</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Updated</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {configs.map((config) => (
                    <tr key={config.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                      <td className="py-3 px-4 text-white font-mono text-sm">{config.key}</td>
                      <td className="py-3 px-4 text-gray-300 font-mono text-sm max-w-xs truncate">
                        {config.value || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 bg-gray-600 rounded text-xs text-gray-300">
                          {config.value_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm max-w-xs truncate">
                        {config.description || '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm">
                        {new Date(config.updated_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => handleEditConfig(config)}
                          disabled={!isSuperAdmin}
                          className={`text-sm ${
                            isSuperAdmin
                              ? 'text-blue-400 hover:text-blue-300'
                              : 'text-gray-600 cursor-not-allowed'
                          }`}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-400">
              No system configurations found. Add configurations via the API or database.
            </div>
          )}
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'audit' && (
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          {isLoadingLogs ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
            </div>
          ) : auditLogs.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-700/50">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Time</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">User ID</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Action</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Resource</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">IP Address</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                      <td className="py-3 px-4 text-gray-400 text-sm">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-white">
                        {log.user_id || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs ${
                            log.action.includes('login')
                              ? 'bg-green-500/20 text-green-400'
                              : log.action.includes('update')
                              ? 'bg-blue-500/20 text-blue-400'
                              : log.action.includes('delete')
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-gray-500/20 text-gray-400'
                          }`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-300 text-sm">
                        {log.resource_type
                          ? `${log.resource_type}${log.resource_id ? `:${log.resource_id}` : ''}`
                          : '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm font-mono">
                        {log.ip_address || '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm max-w-xs truncate">
                        {log.details ? JSON.stringify(log.details) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-400">
              No audit logs found.
            </div>
          )}
        </div>
      )}

      {/* Edit Config Modal */}
      {editingConfig && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-white mb-4">
              Edit Configuration
            </h3>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Key
              </label>
              <input
                type="text"
                value={editingConfig.key}
                disabled
                className="w-full px-4 py-2 bg-gray-600 border border-gray-500 rounded-lg text-gray-400"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Value ({editingConfig.value_type})
              </label>
              {editingConfig.value_type === 'bool' ? (
                <select
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              ) : editingConfig.value_type === 'json' ? (
                <textarea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  rows={5}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              ) : (
                <input
                  type={editingConfig.value_type === 'int' || editingConfig.value_type === 'float' ? 'number' : 'text'}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  step={editingConfig.value_type === 'float' ? '0.01' : undefined}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              )}
            </div>

            {editingConfig.description && (
              <p className="text-gray-400 text-sm mb-4">{editingConfig.description}</p>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleSaveConfig}
                disabled={isSaving}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                onClick={() => setEditingConfig(null)}
                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPage;
