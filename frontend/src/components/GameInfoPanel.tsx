import React, { useRef, useEffect } from "react";
import { useSelector } from "react-redux";
import { motion, AnimatePresence } from "framer-motion";
import { RootState } from "../store";

interface GameInfoPanelProps {
  showThinking?: boolean;
}

export const GameInfoPanel: React.FC<GameInfoPanelProps> = ({ showThinking = false }) => {
  const chatHistory = useSelector((s: RootState) => s.game.chatHistory);
  const gameState = useSelector((s: RootState) => s.game.gameState);
  const agentThinking = useSelector((s: RootState) => s.game.agentThinking);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // 获取所有 AI 玩家的映射
  const agentMap: Record<string, string> = {};
  gameState?.players.forEach(p => {
    if (!p.isHuman) {
      agentMap[p.id] = p.name;
    }
  });

  return (
    <div className="h-full flex flex-col bg-gray-900 border-l border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800 flex-shrink-0">
        <h2 className="text-cyan-400 font-mono text-sm font-bold tracking-widest">
          {showThinking ? "THINKING & CHAT" : "GAME LOG"}
        </h2>
      </div>

      {/* Current thinking (if shown) */}
      {showThinking && (
        <div className="px-3 py-2 border-b border-gray-700 bg-gray-850 flex-shrink-0 max-h-64 overflow-y-auto">
          <div className="space-y-3">
            {Object.entries(agentThinking).map(([agentId, state]) => {
              if (!state?.thinking && !state?.isStreaming) return null;
              return (
                <div key={agentId} className="text-xs bg-gray-800 rounded p-2 border border-gray-700">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-cyan-400 font-mono font-bold">
                      {agentMap[agentId] || agentId}
                    </span>
                    {state?.isStreaming && (
                      <span className="text-yellow-400 animate-pulse">思考中...</span>
                    )}
                  </div>
                  <div className="text-gray-400 font-mono text-[10px] leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {state?.thinking || ""}
                  </div>
                </div>
              );
            })}
            {Object.values(agentThinking).every(s => !s?.isStreaming && !s?.thinking) && (
              <div className="text-gray-600 text-center text-xs font-mono">
                等待 AI 决策...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat history */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <AnimatePresence initial={false}>
          {chatHistory.length === 0 ? (
            <div className="text-gray-600 text-center text-xs mt-8 font-mono">
              No messages yet
            </div>
          ) : (
            chatHistory.map((msg, i) => {
              const senderName = msg.sender === "player_human" ? "You" : (agentMap[msg.sender] || msg.sender);
              const isAction = msg.type === "action";
              const isSystem = msg.type === "system";

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-xs"
                >
                  {isSystem ? (
                    <div className="px-2 py-1 rounded bg-green-900 bg-opacity-30 text-green-400 border-l-2 border-green-500 text-center">
                      <span className="font-mono">⚡ {msg.message}</span>
                    </div>
                  ) : (
                    <div className={
                      "px-2 py-1 rounded " +
                      (isAction
                        ? "bg-gray-800 text-gray-400 border-l-2 border-gray-600"
                        : "bg-gray-800 text-yellow-200 border-l-2 border-yellow-600")
                    }>
                      <span className={isAction ? "text-gray-500" : "text-yellow-400"}>
                        {senderName}:
                      </span>
                      <span className="ml-1 italic">{msg.message}</span>
                    </div>
                  )}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
