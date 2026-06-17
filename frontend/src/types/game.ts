export enum GamePhase {
  PRE_FLOP = "pre_flop",
  FLOP = "flop",
  TURN = "turn",
  RIVER = "river",
  SHOWDOWN = "showdown",
  ENDED = "ended",
}

export enum PlayerStatus {
  ACTIVE = "active",
  FOLDED = "folded",
  ALLIN = "allin",
}

export enum ActionType {
  FOLD = "fold",
  CHECK = "check",
  CALL = "call",
  RAISE = "raise",
  ALLIN = "allin",
}

export interface Card {
  rank: number;
  suit: number;
  toString(): string;
}

export interface Player {
  id: string;
  name: string;
  stack: number;
  currentBet: number;
  holeCards?: Card[];
  status: PlayerStatus;
  position: string;
  isHuman?: boolean;
  agentConfig?: any;
}

export interface GameState {
  gameId?: string;
  phase: GamePhase;
  pot: number;
  streetBet: number;
  communityCards: Card[];
  players: Player[];
  dealerIndex: number;
  actionHistory?: Action[];
}

export interface Allocation {
  playerId: string;
  playerName: string;
  amount: number;
  bestHand: string[];
  handRank: string;
  stackChange: number;
  reason: "showdown" | "last_standing" | "no_win";
}

export interface Action {
  playerId: string;
  type: ActionType;
  amount: number;
  phase: string;
}

export interface AgentThinkingState {
  agentId: string;
  thinking: string;
  speech: string;
  isStreaming: boolean;
  action?: ActionType;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  gameId?: string;
  timestamp?: number;
}

export interface ChatMessage {
  sender: string;
  message: string;
  timestamp: number;
  type: "thinking" | "speech" | "action" | "system";
}

export interface UIState {
  expandedAgents: Set<string>;
  selectedPlayer?: string;
  showChatHistory: boolean;
}
