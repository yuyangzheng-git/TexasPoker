import React from "react";
import { motion } from "framer-motion";

interface CardProps {
  rank?: number;
  suit?: number;
  faceDown?: boolean;
  animate?: boolean;
  small?: boolean;
}

const rankNames: Record<number, string> = {
  2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10",
  11: "J", 12: "Q", 13: "K", 14: "A",
};

const suitSymbols: Record<number, string> = {
  0: "♠",
  1: "♥",
  2: "♦",
  3: "♣",
};

const suitColors: Record<number, string> = {
  0: "text-gray-900",
  1: "text-red-600",
  2: "text-red-600",
  3: "text-gray-900",
};

export const Card: React.FC<CardProps> = ({
  rank = 14,
  suit = 0,
  faceDown = false,
  animate = false,
  small = false,
}) => {
  const cardVariants = {
    flip: {
      rotateY: [0, 90, 0],
      transition: { duration: 0.5 },
    },
    slide: {
      x: [-40, 0],
      opacity: [0, 1],
      transition: { duration: 0.3 },
    },
  };

  const sizeCls = small ? "w-10 h-14" : "w-20 h-28";

  if (faceDown) {
    return (
      <motion.div
        className={`${sizeCls} rounded-lg bg-gradient-to-br from-poker-table to-poker-felt
                   border border-poker-goldDim shadow flex items-center justify-center
                   text-poker-gold font-bold ${small ? "text-lg" : "text-3xl"}`}
        animate={animate ? "flip" : undefined}
        variants={cardVariants}
      >
        ?
      </motion.div>
    );
  }

  const rankStr = rankNames[rank];
  const suitStr = suitSymbols[suit];
  const suitColor = suitColors[suit];

  if (small) {
    // Small card: centered rank with suit below
    return (
      <motion.div
        className={`${sizeCls} rounded bg-white border border-gray-300 shadow-sm
                   flex flex-col items-center justify-center font-bold`}
        animate={animate ? "slide" : undefined}
        variants={cardVariants}
      >
        <span className={`text-sm leading-none ${suitColor}`}>{rankStr}</span>
        <span className={`text-xs leading-none mt-px ${suitColor}`}>{suitStr}</span>
      </motion.div>
    );
  }

  // Normal card: traditional corner markings
  return (
    <motion.div
      className={`${sizeCls} rounded-lg bg-white border border-gray-300 shadow
                 flex flex-col items-center justify-between p-1 font-bold`}
      animate={animate ? "slide" : undefined}
      variants={cardVariants}
    >
      <div className={`flex flex-col items-center leading-none ${suitColor}`}>
        <span className="text-base">{rankStr}</span>
        <span className="text-xs -mt-0.5">{suitStr}</span>
      </div>
      <div className={`text-3xl ${suitColor}`}>{suitStr}</div>
      <div className={`flex flex-col items-center leading-none ${suitColor} rotate-180`}>
        <span className="text-base">{rankStr}</span>
        <span className="text-xs -mt-0.5">{suitStr}</span>
      </div>
    </motion.div>
  );
};
