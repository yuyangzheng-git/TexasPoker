import React from "react";
import { Player, PlayerStatus } from "../types/game";
import { Card } from "./Card";

interface PlayerSeatProps {
  player: Player;
  isShowdown?: boolean;
  isActing?: boolean;
  isDealer?: boolean;
}

const PlayerSeat: React.FC<PlayerSeatProps> = ({ player, isShowdown = false, isActing = false, isDealer = false }) => {
  const isFolded = player.status === PlayerStatus.FOLDED;
  const isAllin = player.status === PlayerStatus.ALLIN;

  // 显示真牌的条件：人类玩家永远可见，摊牌时所有非弃牌玩家可见
  const showFaceUp = player.isHuman || (isShowdown && !isFolded);

  // 位置标签样式
  const positionColor: Record<string, string> = {
    "BTN": "bg-cyan-700 text-cyan-200",
    "BTN/SB": "bg-cyan-700 text-cyan-200",
    "SB": "bg-yellow-700 text-yellow-200",
    "BB": "bg-orange-700 text-orange-200",
    "UTG": "bg-red-800 text-red-200",
    "EP": "bg-red-800 text-red-200",
    "MP": "bg-gray-600 text-gray-200",
    "LJ": "bg-gray-600 text-gray-200",
    "HJ": "bg-gray-600 text-gray-200",
    "CO": "bg-green-700 text-green-200",
  };
  const posColor = positionColor[player.position] || "bg-gray-700 text-gray-300";

  return (
    <div className={
      "relative bg-gray-800 rounded-lg p-2 border-2 transition-all duration-300 " +
      (isActing
        ? "border-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.5)] animate-pulse"
        : "border-gray-700") +
      (isFolded ? " opacity-40" : "")
    }>
      {/* Acting indicator */}
      {isActing && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full animate-ping" />
      )}
      {/* Dealer button */}
      {isDealer && (
        <div className="absolute -top-2 -left-2 w-6 h-6 bg-white rounded-full border-2 border-gray-800 flex items-center justify-center shadow-lg">
          <span className="text-black text-[10px] font-bold">D</span>
        </div>
      )}
      {/* Top row: name + position + status */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1 min-w-0">
          <span className={`shrink-0 text-[9px] font-mono font-bold px-1 rounded ${posColor}`}>
            {player.position}
          </span>
          <span className="text-white font-bold text-xs truncate">{player.name}</span>
          {player.isHuman && (
            <span className="text-yellow-400 text-[10px] font-mono shrink-0">(YOU)</span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {isFolded && <span className="text-red-400 text-[10px] font-bold">FOLD</span>}
          {isAllin && <span className="text-yellow-400 text-[10px] font-bold animate-pulse">ALL-IN</span>}
        </div>
      </div>

      {/* Bottom row: stack + cards */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 font-mono text-xs">${player.stack.toFixed(0)}</span>
          {player.currentBet > 0 && (
            <span className="bg-yellow-800 border border-yellow-600 text-yellow-300 font-mono text-[10px] px-1.5 py-0.5 rounded font-bold">
              BET ${player.currentBet.toFixed(0)}
            </span>
          )}
        </div>

        {/* Cards */}
        {player.holeCards && player.holeCards.length > 0 ? (
          <div className="flex gap-0.5">
            {player.holeCards.map((card, i) => (
              <Card key={i} rank={card.rank} suit={card.suit} faceDown={!showFaceUp} small />
            ))}
          </div>
        ) : !isFolded ? (
          <div className="flex gap-0.5">
            <Card faceDown small />
            <Card faceDown small />
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default PlayerSeat;
