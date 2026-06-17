/**
 * AI Agents Page - AI agent configuration management
 */
import React, { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { AIAgentConfig, AIAgentConfigUpdate } from '../../types/auth';

const AIAgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AIAgentConfig[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingAgent, setEditingAgent] = useState<AIAgentConfig | null>(null);
  const [editForm, setEditForm] = useState<AIAgentConfigUpdate>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadAgents();
  }, [includeInactive]);

  const loadAgents = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.listAIAgents(includeInactive);
      setAgents(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditAgent = (agent: AIAgentConfig) => {
    setEditingAgent(agent);
    setEditForm({
      name: agent.name,
      style: agent.style || '',
      temperature: agent.temperature,
      vpip_target: agent.vpip_target,
      pfr_target: agent.pfr_target,
      risk_profile: agent.risk_profile || '',
      is_active: agent.is_active,
    });
  };

  const handleSaveAgent = async () => {
    if (!editingAgent) return;

    try {
      setIsSaving(true);
      await adminApi.updateAIAgent(editingAgent.agent_id, editForm);
      setEditingAgent(null);
      loadAgents();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">AI Agent Configuration</h1>
        <p className="text-gray-400 mt-1">Manage AI opponent settings and behavior</p>
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
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
          />
          <span className="text-gray-300">Show inactive agents</span>
        </label>
      </div>

      {/* Agents Grid */}
      {isLoading ? (
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className={`bg-gray-800 rounded-xl p-6 border-2 transition-colors ${
                agent.is_active
                  ? 'border-transparent hover:border-purple-500/50'
                  : 'border-transparent opacity-60'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-white">{agent.name}</h3>
                  <p className="text-gray-400 text-sm">{agent.agent_id}</p>
                </div>
                <span
                  className={`px-2 py-1 rounded text-xs ${
                    agent.is_active
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {agent.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Style</span>
                  <span className="text-white">{agent.style || '-'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Temperature</span>
                  <span className="text-white">{agent.temperature}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">VPIP Target</span>
                  <span className="text-white">{(agent.vpip_target * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">PFR Target</span>
                  <span className="text-white">{(agent.pfr_target * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Risk Profile</span>
                  <span className="text-white">{agent.risk_profile || '-'}</span>
                </div>
              </div>

              <button
                onClick={() => handleEditAgent(agent)}
                className="w-full py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Edit Configuration
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {editingAgent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-6">
              Edit Agent: {editingAgent.name}
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={editForm.name || ''}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Style
                </label>
                <input
                  type="text"
                  value={editForm.style || ''}
                  onChange={(e) => setEditForm({ ...editForm, style: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Temperature ({editForm.temperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={editForm.temperature || 0.7}
                  onChange={(e) => setEditForm({ ...editForm, temperature: parseFloat(e.target.value) })}
                  className="w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    VPIP Target ({((editForm.vpip_target || 0) * 100).toFixed(0)}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={editForm.vpip_target || 0.25}
                    onChange={(e) => setEditForm({ ...editForm, vpip_target: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    PFR Target ({((editForm.pfr_target || 0) * 100).toFixed(0)}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={editForm.pfr_target || 0.15}
                    onChange={(e) => setEditForm({ ...editForm, pfr_target: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Risk Profile
                </label>
                <select
                  value={editForm.risk_profile || ''}
                  onChange={(e) => setEditForm({ ...editForm, risk_profile: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Select...</option>
                  <option value="tight-passive">Tight Passive</option>
                  <option value="tight-aggressive">Tight Aggressive</option>
                  <option value="loose-passive">Loose Passive</option>
                  <option value="loose-aggressive">Loose Aggressive</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>

              <div>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editForm.is_active ?? true}
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                    className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-gray-300">Agent Active</span>
                </label>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSaveAgent}
                disabled={isSaving}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded-lg transition-colors"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                onClick={() => setEditingAgent(null)}
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

export default AIAgentsPage;
