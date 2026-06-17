/**
 * Authentication type definitions
 */

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'user' | 'admin' | 'super_admin';
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface PlayerStats {
  id: number;
  user_id: number;
  total_games: number;
  total_hands: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_chips_won: number;
  total_chips_lost: number;
  biggest_pot_won: number;
  vpip: number;
  pfr: number;
  aggression_factor: number;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserWithStats {
  user: User;
  stats: PlayerStats | null;
}

export interface PasswordChangeRequest {
  old_password: string;
  new_password: string;
}

export interface UserUpdateRequest {
  username?: string;
  email?: string;
}

// Admin types
export interface UserAdminUpdate {
  role?: string;
  is_active?: boolean;
}

export interface OverviewStats {
  total_users: number;
  active_users: number;
  total_games: number;
  games_today: number;
  total_hands_played: number;
  active_ai_agents: number;
}

export interface DailyGameStats {
  date: string;
  games_count: number;
  hands_count: number;
  unique_players: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  total_chips_won: number;
  win_rate: number;
  total_games: number;
}

export interface GameSession {
  id: number;
  game_id: string;
  user_id: number | null;
  started_at: string;
  ended_at: string | null;
  total_hands: number;
  starting_stack: number;
  ending_stack: number | null;
  result: string | null;
  ai_opponents: string[];
  small_blind: number;
  big_blind: number;
}

export interface AIAgentConfig {
  id: number;
  agent_id: string;
  name: string;
  style: string | null;
  persona: string | null;
  speech_style: string | null;
  temperature: number;
  vpip_target: number;
  pfr_target: number;
  risk_profile: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIAgentConfigUpdate {
  name?: string;
  style?: string;
  persona?: string;
  speech_style?: string;
  temperature?: number;
  vpip_target?: number;
  pfr_target?: number;
  risk_profile?: string;
  is_active?: boolean;
}

export interface SystemConfig {
  id: number;
  key: string;
  value: string | null;
  value_type: string;
  description: string | null;
  updated_at: string;
  updated_by: number | null;
}

export interface SystemConfigUpdate {
  value: string;
  value_type?: string;
  description?: string;
}

export interface SystemStatus {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  active_games: number;
  active_connections: number;
  uptime_seconds: number;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  [key: string]: T[] | number;
}
