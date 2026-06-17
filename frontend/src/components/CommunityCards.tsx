import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "./Card";
import { GamePhase } from "../types/game";

interface CommunityCardsProps {
  cards: Array<{ rank: number; suit: number }>;
  pot: number;
  phase: GamePhase;
  streetBet: number;
}

const phaseLabels: Record<string, string> = {
  pre_flop: "PRE-FLOP",
  flop: "FLOP",
  turn: "TURN",
  river: "RIVER",
  showdown: "SHOWDOWN",
  ended: "ENDED",
};

export const CommunityCards: React.FC<CommunityCardsProps> = ({ cards, pot, phase, streetBet }) => {
  return (
    <div className="flex flex-col items-center gap-2">
      {/* Phase label */}
      <div className="text-[10px] font-mono text-cyan-400 tracking-widest border border-cyan-800 rounded px-2 py-0.5">
        {phaseLabels[phase] ?? phase}
      </div>

      {/* Cards */}
      <div className="flex gap-1">
        <AnimatePresence>
          {Array(5).fill(null).map((_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              {cards[i]
                ? <Card rank={cards[i].rank} suit={cards[i].suit} animate={true} small />
                : <div className="w-10 h-14 rounded-lg border border-dashed border-gray-600 opacity-30" />
              }
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Pot */}
      <motion.div
        className="bg-black bg-opacity-50 border border-yellow-700 rounded-lg px-3 py-1 text-center"
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        key={pot}
      >
        <p className="text-yellow-400 font-mono font-bold text-sm">
          POT: ${pot.toFixed(0)}
        </p>
        {streetBet > 0 && (
          <p className="text-gray-400 text-[10px] font-mono">
            Current bet: ${streetBet.toFixed(0)}
          </p>
        )}
      </motion.div>
    </div>
  );
};
