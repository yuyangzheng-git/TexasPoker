import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { GameState, AgentThinkingState, ChatMessage, UIState, GamePhase } from "../types/game";

interface PlayerActionRequest {
  isHumanTurn: boolean;
  callAmount: number;
  pot: number;
  validActions: string[];
  timeLimit: number;
}

interface GameStoreState {
  gameState?: GameState;
  agentThinking: Record<string, AgentThinkingState>;
  chatHistory: ChatMessage[];
  uiState: UIState;
  connected: boolean;
  playerActionRequest: PlayerActionRequest;
  gameResult?: { allocations: any[]; finalState?: any };
  currentActingPlayerId?: string;
  isPaused: boolean;
  revealedCards?: Record<string, { rank: number; suit: number }[]>;  // playerId -> hole cards
}

const initialState: GameStoreState = {
  gameState: undefined,
  agentThinking: {},
  chatHistory: [],
  uiState: {
    expandedAgents: new Set(),
    showChatHistory: true,
  },
  connected: false,
  playerActionRequest: {
    isHumanTurn: false,
    callAmount: 0,
    pot: 0,
    validActions: [],
    timeLimit: 30000,
  },
  gameResult: undefined,
  currentActingPlayerId: undefined,
  isPaused: false,
  revealedCards: undefined,
};

const gameSlice = createSlice({
  name: "game",
  initialState,
  reducers: {
    setGameState: (state, action: PayloadAction<GameState>) => {
      state.gameState = action.payload;
    },
    updateGameState: (state, action: PayloadAction<Partial<GameState>>) => {
      if (state.gameState) {
        state.gameState = { ...state.gameState, ...action.payload };
      }
    },
    initAgentThinking: (state, action: PayloadAction<string>) => {
      const agentId = action.payload;
      state.agentThinking[agentId] = {
        agentId,
        thinking: "",
        speech: "",
        isStreaming: true,
      };
    },
    appendThinkingChunk: (
      state,
      action: PayloadAction<{ agentId: string; chunk: string }>
    ) => {
      const { agentId, chunk } = action.payload;
      if (!state.agentThinking[agentId]) {
        state.agentThinking[agentId] = {
          agentId,
          thinking: "",
          speech: "",
          isStreaming: true,
        };
      }
      state.agentThinking[agentId].thinking += chunk;
    },
    completeAgentThinking: (
      state,
      action: PayloadAction<{ agentId: string; speech: string }>
    ) => {
      const { agentId, speech } = action.payload;
      if (state.agentThinking[agentId]) {
        state.agentThinking[agentId].isStreaming = false;
        state.agentThinking[agentId].speech = speech;
      }
    },
    addChatMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.chatHistory.push(action.payload);
      if (state.chatHistory.length > 50) {
        state.chatHistory.shift();
      }
    },
    toggleExpandAgent: (state, action: PayloadAction<string>) => {
      const agentId = action.payload;
      if (state.uiState.expandedAgents.has(agentId)) {
        state.uiState.expandedAgents.delete(agentId);
      } else {
        state.uiState.expandedAgents.add(agentId);
      }
    },
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.connected = action.payload;
    },
    setPlayerActionRequest: (state, action: PayloadAction<PlayerActionRequest>) => {
      state.playerActionRequest = action.payload;
    },
    clearPlayerActionRequest: (state) => {
      state.playerActionRequest = { ...initialState.playerActionRequest };
    },
    setGameResult: (state, action: PayloadAction<{ allocations: any[]; finalState?: any }>) => {
      state.gameResult = action.payload;
      if (action.payload.finalState) {
        state.gameState = { ...state.gameState, ...action.payload.finalState } as GameState;
      }
      if (state.gameState) {
        state.gameState.phase = GamePhase.ENDED;
      }
    },
    resetGame: (state) => {
      state.gameState = undefined;
      state.agentThinking = {};
      state.chatHistory = [];
      state.uiState = {
        expandedAgents: new Set(),
        showChatHistory: true,
      };
      state.playerActionRequest = { ...initialState.playerActionRequest };
      state.gameResult = undefined;
      state.currentActingPlayerId = undefined;
      state.revealedCards = undefined;
    },
    setCurrentActingPlayer: (state, action: PayloadAction<string | undefined>) => {
      state.currentActingPlayerId = action.payload;
    },
    setPaused: (state, action: PayloadAction<boolean>) => {
      state.isPaused = action.payload;
    },
    setRevealedCards: (state, action: PayloadAction<Record<string, { rank: number; suit: number }[]>>) => {
      state.revealedCards = action.payload;
    },
    clearRevealedCards: (state) => {
      state.revealedCards = undefined;
    },
  },
});

export const {
  setGameState,
  updateGameState,
  initAgentThinking,
  appendThinkingChunk,
  completeAgentThinking,
  addChatMessage,
  toggleExpandAgent,
  setConnected,
  setPlayerActionRequest,
  clearPlayerActionRequest,
  setGameResult,
  resetGame,
  setCurrentActingPlayer,
  setPaused,
  setRevealedCards,
  clearRevealedCards,
} = gameSlice.actions;

export default gameSlice.reducer;
