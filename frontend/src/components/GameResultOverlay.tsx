import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Allocation } from "../types/game";

interface GameResultOverlayProps {
  visible: boolean;
  allocations: Allocation[];
  playerName: string;
  onContinue?: () => void;
}

export const GameResultOverlay: React.FC<GameResultOverlayProps> = ({
  visible,
  allocations,
  playerName,
  onContinue,
}) => {
  const [confirmed, setConfirmed] = useState(false);

  // 计算玩家是否获胜
  const playerWon = allocations.some(
    (a) => a.playerId === "player_human" && a.stackChange > 0
  );
  const totalPot = allocations.reduce(
    (sum, a) => sum + (a.amount || 0),
    0
  );

  // 获取原因的中文翻译
  const getReasonText = (reason: string) => {
    const reasonMap: Record<string, string> = {
      showdown: "摊牌获胜",
      last_standing: "其他人弃牌",
      no_win: "未获胜",
      tournament_winner: "锦标赛冠军",
    };
    return reasonMap[reason] || reason;
  };

  const handleContinue = () => {
    setConfirmed(true);
    setTimeout(() => {
      onContinue?.();
      setConfirmed(false);
    }, 300);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-2xl w-full mx-4 text-center shadow-2xl"
            initial={{ scale: 0.8, y: 40 }}
            animate={{ scale: 1, y: 0 }}
            transition={{ type: "spring", damping: 20 }}
          >
            {/* Trophy / Result icon */}
            <div className="text-6xl mb-4">
              {playerWon ? "🏆" : "💀"}
            </div>

            {/* Title */}
            <h1
              className={
                "text-3xl font-bold font-mono tracking-wider mb-6 " +
                (playerWon ? "text-yellow-400" : "text-red-400")
              }
            >
              {playerWon ? "YOU WIN!" : "HAND LOST"}
            </h1>

            {/* Settlement details */}
            <div className="bg-gray-800 rounded-xl p-4 mb-6 space-y-2 text-left max-h-80 overflow-y-auto">
              <div className="text-xs text-gray-400 font-mono mb-3 pb-2 border-b border-gray-700">
                SETTLEMENT
              </div>
              {allocations.map((alloc, i) => {
                const change = alloc.stackChange || 0;
                const isHuman = alloc.playerId === "player_human";
                // 优先使用后端返回的 playerName，否则用本地 playerName
                const displayName = isHuman
                  ? playerName
                  : (alloc.playerName || alloc.playerId);

                return (
                  <div
                    key={i}
                    className={
                      "flex flex-col px-3 py-2 rounded-lg " +
                      (isHuman
                        ? "bg-yellow-900 bg-opacity-30"
                        : "bg-gray-750")
                    }
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span
                          className={
                            "font-mono font-bold text-sm " +
                            (isHuman
                              ? "text-yellow-300"
                              : "text-gray-300")
                          }
                        >
                          {displayName}
                        </span>
                        {alloc.reason && (
                          <span className="text-gray-500 text-[10px] font-mono">
                            ({getReasonText(alloc.reason)})
                          </span>
                        )}
                      </div>
                      <span
                        className={
                          "font-mono font-bold text-sm " +
                          (change > 0 ? "text-green-400" : change < 0 ? "text-red-400" : "text-gray-500")
                        }
                      >
                        {change > 0 ? "+" : ""}{change.toFixed(0)}
                      </span>
                    </div>
                    {/* 显示牌型和最佳手牌 */}
                    {alloc.handRank && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-cyan-400 text-xs font-mono">
                          {alloc.handRank}
                        </span>
                        {alloc.bestHand && alloc.bestHand.length > 0 && (
                          <span className="text-gray-400 text-xs font-mono">
                            [{alloc.bestHand.join(" ")}]
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              <div className="border-t border-gray-700 pt-2 flex justify-between items-center px-3">
                <span className="text-gray-400 font-mono text-xs">
                  Total Pot
                </span>
                <span className="text-yellow-400 font-mono font-bold">
                  ${totalPot.toFixed(0)}
                </span>
              </div>
            </div>

            {/* Continue button */}
            <motion.button
              className="w-full py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold font-mono tracking-wide transition-all active:scale-95"
              onClick={handleContinue}
              disabled={confirmed}
              animate={confirmed ? { scale: 0.95 } : { scale: 1 }}
            >
              {confirmed ? "CONTINUING..." : "CONTINUE TO NEXT HAND"}
            </motion.button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
