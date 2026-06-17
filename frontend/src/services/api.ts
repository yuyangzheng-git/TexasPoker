/**
 * API service for authentication and admin operations
 */
import {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  PasswordChangeRequest,
  UserUpdateRequest,
  UserAdminUpdate,
  OverviewStats,
  DailyGameStats,
  LeaderboardEntry,
  GameSession,
  AIAgentConfig,
  AIAgentConfigUpdate,
  SystemConfig,
  SystemConfigUpdate,
  SystemStatus,
  AuditLog,
  PlayerStats,
} from '../types/auth';

// API base URL
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Token storage
const TOKEN_KEY = 'poker_auth_token';

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

// Helper for making authenticated requests
const authFetch = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 - token expired
  if (response.status === 401) {
    removeToken();
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  return response;
};

// ============== Game API ==============

export interface CreateGameRequest {
  player_name: string;
  num_agents?: number;
  agent_ids?: string[];
  table_size?: number;
  ai_fill_enabled?: boolean;
  ai_difficulty_level?: string;   // "easy" | "medium" | "hard" | "mixed"
  ai_persona_theme?: string;      // "aggressive" | "balanced" | "beginner_friendly" | "random"
  preferred_ai_personas?: string[];
  seat_arrangement?: {
    player_seat: number;
    agent_seats: Array<{ seat: number; agent_id: string }>;
  };
}

export interface CreateGameResponse {
  gameId: string;
  wsUrl: string;
  players: Array<{ id: string; name: string; stack: number }>;
}

export const gameApi = {
  async createGame(data: CreateGameRequest): Promise<CreateGameResponse> {
    const response = await fetch(`${API_BASE}/api/games`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error((error as any).detail || "Failed to create game");
    }

    return response.json();
  },
};

// ============== Auth API ==============

export const authApi = {
  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    const result = await response.json();
    setToken(result.access_token);
    return result;
  },

  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const result = await response.json();
    setToken(result.access_token);
    return result;
  },

  async getMe(): Promise<User> {
    const response = await authFetch('/api/auth/me');

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    return response.json();
  },

  async updateMe(data: UserUpdateRequest): Promise<User> {
    const response = await authFetch('/api/auth/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Update failed');
    }

    return response.json();
  },

  async changePassword(data: PasswordChangeRequest): Promise<void> {
    const response = await authFetch('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password change failed');
    }
  },

  async getMyStats(): Promise<{ user: User; stats: PlayerStats }> {
    const response = await authFetch('/api/auth/me/stats');

    if (!response.ok) {
      throw new Error('Failed to get stats');
    }

    return response.json();
  },

  logout(): void {
    removeToken();
  },
};

// ============== Admin API ==============

export const adminApi = {
  // Users
  async listUsers(params: {
    page?: number;
    page_size?: number;
    search?: string;
    role?: string;
    is_active?: boolean;
  } = {}): Promise<{
    users: User[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.search) searchParams.set('search', params.search);
    if (params.role) searchParams.set('role', params.role);
    if (params.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());

    const response = await authFetch(`/api/admin/users?${searchParams}`);

    if (!response.ok) {
      throw new Error('Failed to list users');
    }

    return response.json();
  },

  async getUser(userId: number): Promise<{
    user: User;
    stats: PlayerStats | null;
    recent_games: GameSession[];
  }> {
    const response = await authFetch(`/api/admin/users/${userId}`);

    if (!response.ok) {
      throw new Error('Failed to get user');
    }

    return response.json();
  },

  async updateUser(userId: number, data: UserAdminUpdate): Promise<User> {
    const response = await authFetch(`/api/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Update failed');
    }

    return response.json();
  },

  // Stats
  async getOverviewStats(): Promise<OverviewStats> {
    const response = await authFetch('/api/admin/stats/overview');

    if (!response.ok) {
      throw new Error('Failed to get overview stats');
    }

    return response.json();
  },

  async getDailyGameStats(days: number = 30): Promise<DailyGameStats[]> {
    const response = await authFetch(`/api/admin/stats/games?days=${days}`);

    if (!response.ok) {
      throw new Error('Failed to get game stats');
    }

    return response.json();
  },

  async getLeaderboard(limit: number = 20): Promise<LeaderboardEntry[]> {
    const response = await authFetch(`/api/admin/stats/leaderboard?limit=${limit}`);

    if (!response.ok) {
      throw new Error('Failed to get leaderboard');
    }

    return response.json();
  },

  // Games
  async listGames(params: {
    page?: number;
    page_size?: number;
    user_id?: number;
    result?: string;
    start_date?: string;
    end_date?: string;
  } = {}): Promise<{
    games: GameSession[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.user_id) searchParams.set('user_id', params.user_id.toString());
    if (params.result) searchParams.set('result', params.result);
    if (params.start_date) searchParams.set('start_date', params.start_date);
    if (params.end_date) searchParams.set('end_date', params.end_date);

    const response = await authFetch(`/api/admin/games?${searchParams}`);

    if (!response.ok) {
      throw new Error('Failed to list games');
    }

    return response.json();
  },

  async getGame(gameId: string): Promise<{
    game: GameSession;
    hands: Array<{
      hand_number: number;
      pot_size: number;
      player_result: string | null;
      chips_change: number;
      final_hand_rank: string | null;
    }>;
    user: User | null;
  }> {
    const response = await authFetch(`/api/admin/games/${gameId}`);

    if (!response.ok) {
      throw new Error('Failed to get game');
    }

    return response.json();
  },

  // AI Agents
  async listAIAgents(includeInactive: boolean = false): Promise<AIAgentConfig[]> {
    const response = await authFetch(
      `/api/admin/ai-agents?include_inactive=${includeInactive}`
    );

    if (!response.ok) {
      throw new Error('Failed to list AI agents');
    }

    return response.json();
  },

  async getAIAgent(agentId: string): Promise<AIAgentConfig> {
    const response = await authFetch(`/api/admin/ai-agents/${agentId}`);

    if (!response.ok) {
      throw new Error('Failed to get AI agent');
    }

    return response.json();
  },

  async updateAIAgent(agentId: string, data: AIAgentConfigUpdate): Promise<AIAgentConfig> {
    const response = await authFetch(`/api/admin/ai-agents/${agentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Update failed');
    }

    return response.json();
  },

  // System Config
  async listSystemConfigs(): Promise<SystemConfig[]> {
    const response = await authFetch('/api/admin/system-config');

    if (!response.ok) {
      throw new Error('Failed to list system configs');
    }

    return response.json();
  },

  async updateSystemConfig(key: string, data: SystemConfigUpdate): Promise<SystemConfig> {
    const response = await authFetch(`/api/admin/system-config/${key}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Update failed');
    }

    return response.json();
  },

  // Monitor
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await authFetch('/api/admin/monitor/status');

    if (!response.ok) {
      throw new Error('Failed to get system status');
    }

    return response.json();
  },

  async listAuditLogs(params: {
    page?: number;
    page_size?: number;
    user_id?: number;
    action?: string;
    resource_type?: string;
    start_date?: string;
  } = {}): Promise<{
    logs: AuditLog[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.user_id) searchParams.set('user_id', params.user_id.toString());
    if (params.action) searchParams.set('action', params.action);
    if (params.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params.start_date) searchParams.set('start_date', params.start_date);

    const response = await authFetch(`/api/admin/monitor/audit-logs?${searchParams}`);

    if (!response.ok) {
      throw new Error('Failed to list audit logs');
    }

    return response.json();
  },
};

export default { gameApi, authApi, adminApi };
