import React, { useCallback, useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { PokerTable } from "../components/PokerTable";
import { GameInfoPanel } from "../components/GameInfoPanel";
import { ActionPanel } from "../components/ActionPanel";
import { GameResultOverlay } from "../components/GameResultOverlay";
import { useWebSocket } from "../hooks/useWebSocket";
import { useSound } from "../hooks/useSound";
import { RootState, AppDispatch } from "../store";
import { ActionType } from "../types/game";
import { setPaused } from "../store/gameSlice";

export const GamePage: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const dispatch: AppDispatch = useDispatch();
  const { submitAction, sendMessage } = useWebSocket(gameId);
  const { playSound } = useSound();
  const [showAgentThinking, setShowAgentThinking] = useState(false);
  const [lastPhase, setLastPhase] = useState<string>("");
  const [lastChatLength, setLastChatLength] = useState(0);

  const gameState = useSelector((s: RootState) => s.game.gameState);
  const connected = useSelector((s: RootState) => s.game.connected);
  const agentThinking = useSelector((s: RootState) => s.game.agentThinking);
  const playerActionRequest = useSelector((s: RootState) => s.game.playerActionRequest);
  const gameResult = useSelector((s: RootState) => s.game.gameResult);
  const chatHistory = useSelector((s: RootState) => s.game.chatHistory);
  const isPaused = useSelector((s: RootState) => s.game.isPaused);

  const humanPlayer = gameState?.players.find(p => p.isHuman);
  const isHumanTurn = playerActionRequest.isHumanTurn;

  // 确定当前行动的玩家
  const getCurrentActingPlayer = () => {
    if (isHumanTurn) {
      return humanPlayer?.name || "Player";
    }
    // 查找正在思考的 agent
    for (const [agentId, thinkingState] of Object.entries(agentThinking)) {
      if (thinkingState?.isStreaming) {
        const agent = gameState?.players.find(p => p.id === agentId);
        return agent?.name || agentId;
      }
    }
    return null;
  };

  const currentActingPlayer = getCurrentActingPlayer();

  // 阶段标签映射
  const phaseLabels: Record<string, string> = {
    pre_flop: "PRE-FLOP",
    flop: "FLOP",
    turn: "TURN",
    river: "RIVER",
    showdown: "SHOWDOWN",
    ended: "ENDED",
  };

  // Play sound for opponent actions
  useEffect(() => {
    if (chatHistory.length > lastChatLength) {
      const newMessage = chatHistory[chatHistory.length - 1];
      // Only play sound for opponent actions (not human player)
      if (newMessage.sender !== "player_human" && newMessage.type === "action") {
        const message = newMessage.message.toLowerCase();
        if (message.includes("fold")) {
          playSound("fold");
        } else if (message.includes("check")) {
          playSound("check");
        } else if (message.includes("raise") || message.includes("call") || message.includes("allin")) {
          playSound("bet");
        }
      }
      setLastChatLength(chatHistory.length);
    }
  }, [chatHistory, lastChatLength, playSound]);

  // Play deal sound when phase changes (new community cards)
  useEffect(() => {
    if (gameState?.phase && gameState.phase !== lastPhase && gameState.phase !== "pre_flop") {
      playSound("deal");
      setLastPhase(gameState.phase);
    }
  }, [gameState?.phase, lastPhase, playSound]);

  // Play win/lose sound when game ends
  useEffect(() => {
    if (gameResult && humanPlayer) {
      const playerAlloc = gameResult.allocations.find(a => a.playerId === humanPlayer.id);
      if (playerAlloc) {
        const stackChange = playerAlloc.stackChange || 0;
        if (stackChange > 0) {
          playSound("win");
        } else if (stackChange < 0) {
          playSound("lose");
        }
      }
    }
  }, [gameResult, humanPlayer, playSound]);

  const handleAction = useCallback(
    (action: ActionType, amount?: number, speech?: string) => {
      if (!humanPlayer) return;

      // Play sound based on action
      if (action === "fold") {
        playSound("fold");
      } else if (action === "check") {
        playSound("check");
      } else if (action === "call" || action === "raise" || action === "allin") {
        playSound("bet");
      }

      submitAction(humanPlayer.id, action, amount, speech);
    },
    [humanPlayer, submitAction, playSound]
  );

  const handleContinueNextHand = useCallback(() => {
    sendMessage({ type: "READY_FOR_NEXT_HAND" });
  }, [sendMessage]);

  // 计算有多少 AI 已完成思考
  const totalAgents = gameState?.players.filter(p => !p.isHuman).length ?? 0;
  const completedAgents = Object.values(agentThinking).filter(a => !a.isStreaming).length;

  const isLoading = !gameState;

  return (
    <div className="h-screen w-screen overflow-hidden bg-gray-950 flex flex-col safe-area-container">
      {/* Top bar */}
      <div className="flex-shrink-0 h-10 sm:h-12 bg-gray-900 border-b border-gray-700 flex items-center px-2 sm:px-4 gap-2 sm:gap-4 z-40">
        <span className="text-cyan-400 font-mono text-xs font-bold tracking-widest">POKER LLM</span>

        {gameState && (
          <>
            {/* Phase display */}
            <div className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-0.5 sm:py-1 bg-gray-800 rounded border border-cyan-600">
              <span className="text-gray-400 font-mono text-[10px] sm:text-xs hidden sm:inline">PHASE:</span>
              <span className="text-cyan-400 font-mono text-[10px] sm:text-xs font-bold">
                {phaseLabels[gameState.phase] || gameState.phase?.toUpperCase()}
              </span>
            </div>

            {/* Current acting player */}
            {currentActingPlayer && (
              <div className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-0.5 sm:py-1 bg-gray-800 rounded border border-yellow-600">
                <span className="text-gray-400 font-mono text-[10px] sm:text-xs hidden sm:inline">ACTING:</span>
                <span className={`font-mono text-[10px] sm:text-xs font-bold ${isHumanTurn ? "text-yellow-300" : "text-orange-300"}`}>
                  {currentActingPlayer}
                </span>
              </div>
            )}

            {/* Pot */}
            <span className="text-yellow-400 font-mono text-[10px] sm:text-xs">
              POT: ${gameState.pot?.toFixed(0) ?? 0}
            </span>
          </>
        )}
        <div className="flex-1" />
        <button
          className={"text-[10px] sm:text-xs font-mono px-2 sm:px-3 py-0.5 sm:py-1 rounded border transition-colors " +
            (isPaused
              ? "bg-yellow-900 border-yellow-500 text-yellow-300"
              : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500")
          }
          onClick={() => {
            dispatch(setPaused(!isPaused));
            sendMessage({ type: isPaused ? "RESUME" : "PAUSE" });
          }}
        >
          {isPaused ? "▶ RESUME" : "⏸ PAUSE"}
        </button>
        <button
          className={"text-[10px] sm:text-xs font-mono px-2 sm:px-3 py-0.5 sm:py-1 rounded border transition-colors " +
            (showAgentThinking
              ? "bg-cyan-900 border-cyan-500 text-cyan-300"
              : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500")
          }
          onClick={() => setShowAgentThinking(v => !v)}
        >
          {showAgentThinking ? "THINKING ON" : "THINKING OFF"}
        </button>
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="flex-1 flex flex-col items-center justify-center bg-gray-950">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-cyan-400 font-mono text-lg font-bold tracking-wider">
              {connected ? "GAME SETUP IN PROGRESS..." : "CONNECTING TO SERVER..."}
            </p>
            <p className="text-gray-500 font-mono text-sm">
              Waiting for AI players to make their first decisions
            </p>
            {connected && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <div className="h-1 w-48 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                    style={{ width: `${totalAgents > 0 ? (completedAgents / totalAgents) * 100 : 10}%` }}
                  />
                </div>
                <span className="text-gray-400 font-mono text-xs">
                  {completedAgents}/{totalAgents}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main game area */}
      {!isLoading && (
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex">
            <PokerTable />
          </div>
          <div className="w-80 flex-shrink-0 border-l border-gray-700">
            <GameInfoPanel showThinking={showAgentThinking} />
          </div>
        </div>
      )}

      {/* Action panel - floating modal */}
      <ActionPanel
        isActive={isHumanTurn}
        callAmount={playerActionRequest.callAmount}
        pot={(playerActionRequest.pot || gameState?.pot) ?? 0}
        myStack={humanPlayer?.stack ?? 1000}
        timeLimit={playerActionRequest.timeLimit}
        onAction={handleAction}
      />

      {/* Game result overlay - waits for player confirmation */}
      <GameResultOverlay
        visible={!!gameResult}
        allocations={gameResult?.allocations ?? []}
        playerName={humanPlayer?.name ?? "Player"}
        onContinue={handleContinueNextHand}
      />
    </div>
  );
};
