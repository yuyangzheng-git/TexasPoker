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
  setPaused,
  setConnectionError,
  setGameFinished,
  setActionSubmitting,
  setActionError,
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
  const requestRef = useRef<string | undefined>();
  const retryRef = useRef<ReturnType<typeof setTimeout>>();
  const stoppedRef = useRef(false);

  const connect = useCallback(() => {
    if (!gameId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws/${gameId}`);

    ws.onopen = () => {
      if (wsRef.current !== ws) return;
      ws.send(JSON.stringify({
        type: "AUTH", sessionToken: sessionStorage.getItem(`poker_session_${gameId}`),
      }));
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return;
      try {
        const msg = JSON.parse(event.data);
        const { type, data } = msg;
        // 将后端 snake_case 转为前端 camelCase
        const converted = convertKeys(data);

        switch (type) {
          case "SESSION_STATE":
            dispatch(resetGame());
            dispatch(setConnected(true));
            dispatch(setConnectionError(undefined));
            dispatch(setGameFinished(data.finished));
            dispatch(setGameState(converted.state));
            dispatch(setPaused(converted.paused));
            if (converted.result) dispatch(setGameResult(converted.result));
            requestRef.current = data.pendingAction?.requestId;
            if (data.pendingAction?.kind === "action") {
              const req = data.pendingAction;
              dispatch(setPlayerActionRequest({
                requestId: req.requestId, isHumanTurn: true, callAmount: req.callAmount, pot: req.pot,
                validActions: req.validActions, timeLimit: req.timeLimit,
                minRaise: req.minRaise, maxRaise: req.maxRaise,
              }));
              dispatch(setCurrentActingPlayer(req.playerId));
            }
            break;
          case "PAUSE_STATE":
            dispatch(setPaused(data.paused));
            break;
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
            if (!data.action) break;
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
            requestRef.current = data.requestId;
            dispatch(setPlayerActionRequest({
              requestId: data.requestId,
              isHumanTurn: true,
              callAmount: data.callAmount ?? 0,
              pot: data.pot ?? 0,
              validActions: data.validActions ?? [],
              timeLimit: data.timeLimit ?? 30000,
              minRaise: data.minRaise,
              maxRaise: data.maxRaise,
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
            requestRef.current = data.requestId;
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
            requestRef.current = data.requestId;
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
            dispatch(setGameFinished(true));
            dispatch(addChatMessage({
              sender: "system",
              message: `比赛结束！${converted?.winner || ""}获胜！`,
              timestamp: Date.now(),
              type: "system",
            } as ChatMessage));
            break;

          case "ERROR":
            dispatch(setActionError(converted?.message || "操作失败，请重试"));
            dispatch(addChatMessage({ sender: "system", message: converted?.message || "操作失败",
              timestamp: Date.now(), type: "system" }));
            break;
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = (event) => {
      if (wsRef.current !== ws) return;
      dispatch(setConnected(false));
      dispatch(clearPlayerActionRequest());
      dispatch(setConnectionError("连接已断开，正在重连…"));
      if (!stoppedRef.current && event.code !== 4403 && event.code !== 4409) {
        retryRef.current = setTimeout(connect, 1500);
      } else if (event.code === 4403 || event.code === 4409) {
        dispatch(setConnectionError(event.code === 4403
          ? "牌局凭证失效，请从大厅重新开始。" : "此牌局已在另一个窗口打开。"));
      }
      console.log("WebSocket disconnected");
    };

    ws.onerror = (err) => {
      if (wsRef.current !== ws) return;
      console.error("WebSocket error:", err);
      dispatch(setConnected(false));
    };

    wsRef.current = ws;
  }, [gameId, dispatch]);

  const disconnect = useCallback(() => {
    stoppedRef.current = true;
    if (retryRef.current) clearTimeout(retryRef.current);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((msg: object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ ...msg, requestId: requestRef.current }));
    }
  }, []);

  const submitAction = useCallback(
    (playerId: string, action: string, amount?: number, speech?: string) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      dispatch(setActionSubmitting(true));
      sendMessage({ type: "ACTION", playerId, action, amount: amount ?? 0, speech: speech || "" });
    },
    [sendMessage, dispatch]
  );

  useEffect(() => {
    stoppedRef.current = false;
    dispatch(resetGame());
    dispatch(setConnectionError(undefined));
    connect();
    return () => disconnect();
  }, [connect, disconnect, dispatch]);

  return { submitAction, sendMessage };
};
