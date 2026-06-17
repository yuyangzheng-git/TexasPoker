import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../store";
import PlayerSeat from "./PlayerSeat";
import { CommunityCards } from "./CommunityCards";
import { GamePhase } from "../types/game";

export const PokerTable: React.FC = () => {
  const gameState = useSelector((s: RootState) => s.game.gameState);
  const currentActingPlayerId = useSelector((s: RootState) => s.game.currentActingPlayerId);
  const revealedCards = useSelector((s: RootState) => s.game.revealedCards);

  if (!gameState) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950">
        <p className="text-gray-500 font-mono text-lg animate-pulse">Waiting for game...</p>
      </div>
    );
  }

  const communityCards = gameState.communityCards ?? [];
  const phase = gameState.phase ?? GamePhase.PRE_FLOP;
  const isShowdownPhase = phase === GamePhase.SHOWDOWN || !!revealedCards;
  const dealerIndex = gameState.dealerIndex ?? 0;

  const playersWithRevealedCards = gameState.players.map(player => {
    if (revealedCards && revealedCards[player.id]) {
      return { ...player, holeCards: revealedCards[player.id] };
    }
    return player;
  });

  return (
    <div className="flex-1 flex bg-gray-950 h-full overflow-hidden">
      {/* Left: player list */}
      <div className="w-56 flex-shrink-0 flex flex-col gap-3 pl-4 pr-2 py-4 overflow-y-auto">
        {playersWithRevealedCards.map((player, index) => (
          <PlayerSeat
            key={player.id}
            player={player}
            isShowdown={isShowdownPhase}
            isActing={player.id === currentActingPlayerId}
            isDealer={index === dealerIndex}
          />
        ))}
      </div>

      {/* Center: oval table */}
      <div className="flex-1 flex items-center justify-center px-2 py-4">
        <div
          className="relative w-full max-w-[500px] aspect-[16/9] rounded-[50%] border-4 border-yellow-900 shadow-[inset_0_0_60px_rgba(0,0,0,0.6)]"
          style={{
            background: "radial-gradient(ellipse at center, #2e7d32 0%, #1b5e20 70%, #0a3d0a 100%)",
            minHeight: 180,
          }}
        >
          <div className="absolute inset-3 rounded-[50%] border border-green-700 opacity-30" />
          <div className="absolute inset-0 flex items-center justify-center px-2">
            <CommunityCards
              cards={communityCards.map(c => ({ rank: c.rank, suit: c.suit }))}
              pot={gameState.pot ?? 0}
              phase={phase}
              streetBet={gameState.streetBet ?? 0}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
