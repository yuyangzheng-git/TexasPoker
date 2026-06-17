import React, { useRef, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { motion, AnimatePresence } from "framer-motion";
import { RootState } from "../store";
import { toggleExpandAgent } from "../store/gameSlice";

interface AgentThinkingPanelProps {
  showThinking?: boolean;
}

export const AgentThinkingPanel: React.FC<AgentThinkingPanelProps> = ({ showThinking = false }) => {
  const dispatch = useDispatch();
  const agentThinking = useSelector((s: RootState) => s.game.agentThinking);
  const gameState = useSelector((s: RootState) => s.game.gameState);
  const agents = gameState?.players.filter(p => !p.isHuman) ?? [];

  return (
    <div className="h-full flex flex-col bg-gray-900 border-l border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800">
        <h2 className="text-cyan-400 font-mono text-sm font-bold tracking-widest">
          {showThinking ? "AGENT THINKING" : "AGENT STATUS"}
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {agents.map(agent => {
          const state = agentThinking[agent.id];
          const isExpanded = true;

          return (
            <motion.div
              key={agent.id}
              className="border border-gray-700 rounded-lg overflow-hidden"
              animate={{ opacity: 1 }}
              initial={{ opacity: 0 }}
            >
              {/* Header */}
              <button
                className="w-full flex items-center justify-between px-3 py-2 bg-gray-800 hover:bg-gray-700 transition-colors"
                onClick={() => dispatch(toggleExpandAgent(agent.id))}
              >
                <div className="flex items-center gap-2">
                  <div className={"w-2 h-2 rounded-full " + (state?.isStreaming ? "bg-cyan-400 animate-pulse" : "bg-gray-500")} />
                  <span className="text-white font-bold text-xs">{agent.name}</span>
                  {state?.isStreaming && (
                    <span className="text-cyan-400 text-xs font-mono">THINKING...</span>
                  )}
                </div>
                <span className="text-gray-500 text-xs">{"$" + agent.stack.toFixed(0)}</span>
              </button>

              <AnimatePresence>
                {isExpanded && state && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: "auto" }}
                    exit={{ height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-3 py-2 bg-gray-900 max-h-48 overflow-y-auto">
                      {showThinking && state.thinking && (
                        <div className="mb-2">
                          <span className="text-green-400 text-xs font-mono font-bold">THINKING</span>
                          <ThinkingStream text={state.thinking} isStreaming={state.isStreaming} />
                        </div>
                      )}
                      {state.speech && (
                        <div className={"border-t border-gray-700 pt-2 " + (showThinking && state.thinking ? "mt-2" : "")}>
                          <span className="text-yellow-400 text-xs font-mono font-bold">SAYS</span>
                          <p className="text-yellow-200 text-xs mt-1 italic">"{state.speech}"</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}

        {agents.length === 0 && (
          <div className="text-gray-600 text-center text-sm mt-8 font-mono">
            No agents connected
          </div>
        )}
      </div>
    </div>
  );
};

const ThinkingStream: React.FC<{ text: string; isStreaming: boolean }> = ({ text, isStreaming }) => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [text]);

  return (
    <div ref={ref} className="mt-1 text-gray-300 text-xs font-mono leading-relaxed whitespace-pre-wrap break-words">
      {text}
      {isStreaming && <span className="animate-pulse text-cyan-400 ml-1">▍</span>}
    </div>
  );
};
