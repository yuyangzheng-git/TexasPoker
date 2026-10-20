/**
 * API service for creating guest tables.
 */
import { API_BASE_URL } from '../config';
const API_BASE = API_BASE_URL;

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
  sessionToken: string;
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
      const detail = (error as any).detail;
      throw new Error(typeof detail === "string" ? detail : "Invalid table settings. Check your name (16 characters max) and try again.");
    }

    const result: CreateGameResponse = await response.json();
    sessionStorage.setItem(`poker_session_${result.gameId}`, result.sessionToken);
    return result;
  },
};
