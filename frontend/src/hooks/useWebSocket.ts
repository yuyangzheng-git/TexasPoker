import { useEffect, useRef, useCallback } from "react";
import { useDispatch } from "react-redux";
import { AppDispatch } from "../store";
import {
  setGameState,
  updateGameState,
  initAgentThinking,
  appendThinkingChunk,
  completeAgentThinking,
  addChatMessage,
  setConnected,
  setPlayerActionRequest,
  clearPlayerActionRequest,
  setGameResult,
  resetGame,
  setCurrentActingPlayer,
  setRevealedCards,
} from "../store/gameSlice";
import { ChatMessage } from "../types/game";
import { WS_BASE_URL } from "../config";

// 将 snake_case 字符串转为 camelCase
function toCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

// 递归转换对象所有 key
function convertKeys(obj: any): any {
  if (obj === null || obj === undefined) return obj;
  if (Array.isArray(obj)) return obj.map(convertKeys);
  if (typeof obj !== "object") return obj;
  const result: Record<string, any> = {};
  for (const [key, value] of Object.entries(obj)) {
    result[toCamel(key)] = convertKeys(value);
  }
  return result;
}

export const useWebSocket = (gameId: string | undefined) => {
  const dispatch: AppDispatch = useDispatch();
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!gameId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws/${gameId}`);

    ws.onopen = () => {
      dispatch(setConnected(true));
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const { type, data } = msg;
        // 将后端 snake_case 转为前端 camelCase
        const converted = convertKeys(data);

        switch (type) {
          case "GAME_CREATED":
          case "GAME_STARTED":
            dispatch(setGameState(converted));
            dispatch(addChatMessage({
              sender: "system",
              message: "游戏开始！",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "PHASE_CHANGED": {
            const phaseNames: Record<string, string> = {
              pre_flop: "翻牌前",
              flop: "翻牌",
              turn: "转牌",
              river: "河牌",
              showdown: "摊牌",
            };
            const phaseName = phaseNames[converted.phase] || converted.phase;
            dispatch(updateGameState(converted));
            dispatch(addChatMessage({
              sender: "system",
              message: `进入 ${phaseName} 阶段`,
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;
          }

          case "AGENT_THINKING_START":
            dispatch(initAgentThinking(data.agentId));
            dispatch(setCurrentActingPlayer(data.agentId));
            dispatch(clearPlayerActionRequest());
            break;

          case "AGENT_THINKING_CHUNK":
            dispatch(appendThinkingChunk({ agentId: data.agentId, chunk: data.chunk }));
            break;

          case "AGENT_THINKING_END":
            dispatch(completeAgentThinking({ agentId: data.agentId, speech: data.speech }));
            dispatch(setCurrentActingPlayer(undefined));
            // 添加行动通知
            const actionNames: Record<string, string> = {
              fold: "弃牌",
              check: "过牌",
              call: "跟注",
              raise: "加注",
              allin: "全押",
            };
            const actionName = actionNames[data.action] || data.action;
            dispatch(
              addChatMessage({
                sender: data.agentId,
                message: `【${actionName}】${data.speech || ""}`,
                timestamp: Date.now(),
                type: "action",
              } as ChatMessage)
            );
            break;

          case "PLAYER_ACTION": {
            if (data.stateSnapshot) {
              dispatch(updateGameState(convertKeys(data.stateSnapshot)));
            } else {
              dispatch(updateGameState({ pot: data.pot }));
            }
            dispatch(setCurrentActingPlayer(undefined));
            dispatch(clearPlayerActionRequest());
            // 显示人类玩家的行动和放话
            if (data.playerId === "player_human" && data.action) {
              const actionNames: Record<string, string> = {
                fold: "弃牌",
                check: "过牌",
                call: "跟注",
                raise: "加注",
                allin: "全押",
              };
              const actionName = actionNames[data.action] || data.action;
              dispatch(
                addChatMessage({
                  sender: data.playerId,
                  message: `【${actionName}】${data.speech || ""}`,
                  timestamp: Date.now(),
                  type: "action",
                } as ChatMessage)
              );
            }
            break;
          }

          case "PLAYER_ACTION_REQUEST": {
            dispatch(setPlayerActionRequest({
              isHumanTurn: true,
              callAmount: data.callAmount ?? 0,
              pot: data.pot ?? 0,
              validActions: data.validActions ?? [],
              timeLimit: data.timeLimit ?? 30000,
            }));
            dispatch(setCurrentActingPlayer(data.playerId));
            dispatch(addChatMessage({
              sender: "system",
              message: "轮到你行动了！",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;
          }

          case "REVEAL_ALL_CARDS": {
            console.log("[WS] Received REVEAL_ALL_CARDS:", data);
            // 将所有玩家的底牌存入状态
            const cardsMap: Record<string, { rank: number; suit: number }[]> = {};
            if (converted.players) {
              for (const p of converted.players) {
                if (p.holeCards) {
                  cardsMap[p.id] = p.holeCards;
                }
              }
            }
            dispatch(setRevealedCards(cardsMap));
            dispatch(updateGameState({ phase: "showdown" as any }));
            dispatch(addChatMessage({
              sender: "system",
              message: "🃏 所有玩家亮牌！",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;
          }

          case "SHOWDOWN":
            console.log("[WS] Received SHOWDOWN:", data);
            dispatch(updateGameState({ phase: "showdown" as any }));
            if (converted?.finalState) dispatch(updateGameState(converted.finalState));
            // 显示摊牌结果 - 确保 allocations 也被转换
            const showdownAllocations = convertKeys(data.allocations) || [];
            console.log("[WS] Setting game result with allocations:", showdownAllocations);
            dispatch(setGameResult({
              allocations: showdownAllocations,
              finalState: converted?.finalState,
            }));
            dispatch(addChatMessage({
              sender: "system",
              message: "摊牌！公布底牌",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "GAME_ENDED":
            console.log("[WS] Received GAME_ENDED:", data);
            const gameEndedAllocations = convertKeys(data.allocations) || [];
            console.log("[WS] Setting game result with allocations:", gameEndedAllocations);
            dispatch(setGameResult({
              allocations: gameEndedAllocations,
              finalState: converted?.finalState,
            }));
            dispatch(addChatMessage({
              sender: "system",
              message: "本局结束",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "HAND_STARTED":
            // 清空上一手的结果，开始新的一手
            dispatch(resetGame());
            dispatch(setGameState(converted?.gameState || converted));
            dispatch(addChatMessage({
              sender: "system",
              message: "新一局开始！",
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "TOURNAMENT_ENDED":
            // 整个比赛结束
            console.log("Tournament ended:", converted);
            dispatch(setGameResult({
              allocations: [{ playerId: converted?.winner, amount: 0, reason: "tournament_winner" }],
              finalState: { finalStacks: converted?.finalStacks },
            }));
            dispatch(addChatMessage({
              sender: "system",
              message: `比赛结束！${converted?.winner || ""}获胜！`,
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "ERROR":
            console.error("Server error:", converted?.message);
            break;
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      dispatch(setConnected(false));
      console.log("WebSocket disconnected");
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      dispatch(setConnected(false));
    };

    wsRef.current = ws;
  }, [gameId, dispatch]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const submitAction = useCallback(
    (playerId: string, action: string, amount?: number, speech?: string) => {
      sendMessage({ playerId, action, amount: amount || 0, speech: speech || "" });
    },
    [sendMessage]
  );

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { submitAction, sendMessage };
};
