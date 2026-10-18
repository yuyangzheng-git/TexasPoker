import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { GameState, AgentThinkingState, ChatMessage, UIState, GamePhase } from "../types/game";

interface PlayerActionRequest {
  requestId?: string;
  isHumanTurn: boolean;
  callAmount: number;
  pot: number;
  validActions: string[];
  timeLimit: number;
  minRaise: number;
  maxRaise: number;
}

interface GameStoreState {
  gameState?: GameState;
  agentThinking: Record<string, AgentThinkingState>;
  chatHistory: ChatMessage[];
  uiState: UIState;
  connected: boolean;
  connectionError?: string;
  gameFinished: boolean;
  actionSubmitting: boolean;
  actionError?: string;
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
    expandedAgents: [],
    showChatHistory: true,
  },
  connected: false,
  gameFinished: false,
  actionSubmitting: false,
  playerActionRequest: {
    isHumanTurn: false,
    callAmount: 0,
    pot: 0,
    validActions: [],
    timeLimit: 30000,
    minRaise: 20,
    maxRaise: 1000,
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
      state.agentThinking[agentId].thinking += `${state.agentThinking[agentId].thinking ? "\n\n" : ""}${chunk}`;
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
      const index = state.uiState.expandedAgents.indexOf(agentId);
      if (index >= 0) state.uiState.expandedAgents.splice(index, 1);
      else state.uiState.expandedAgents.push(agentId);
    },
    setActionSubmitting: (state, action: PayloadAction<boolean>) => {
      state.actionSubmitting = action.payload;
      if (action.payload) state.actionError = undefined;
    },
    setActionError: (state, action: PayloadAction<string>) => {
      state.actionError = action.payload;
      state.actionSubmitting = false;
    },
    setConnectionError: (state, action: PayloadAction<string | undefined>) => {
      state.connectionError = action.payload;
    },
    setGameFinished: (state, action: PayloadAction<boolean>) => {
      state.gameFinished = action.payload;
    },
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.connected = action.payload;
    },
    setPlayerActionRequest: (state, action: PayloadAction<PlayerActionRequest>) => {
      state.playerActionRequest = action.payload;
      state.actionSubmitting = false;
      state.actionError = undefined;
    },
    clearPlayerActionRequest: (state) => {
      state.playerActionRequest = { ...initialState.playerActionRequest };
      state.actionSubmitting = false;
      state.actionError = undefined;
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
        expandedAgents: [],
        showChatHistory: true,
      };
      state.playerActionRequest = { ...initialState.playerActionRequest };
      state.actionSubmitting = false;
      state.actionError = undefined;
      state.gameResult = undefined;
      state.gameFinished = false;
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
  setConnectionError,
  setActionSubmitting,
  setActionError,
  setGameFinished,
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
