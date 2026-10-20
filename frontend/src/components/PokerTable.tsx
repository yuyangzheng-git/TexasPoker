import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import PlayerSeat from './PlayerSeat';
import { CommunityCards } from './CommunityCards';
import { GamePhase } from '../types/game';
export const PokerTable: React.FC = () => {
  const game = useSelector((s: RootState) => s.game.gameState);
  const acting = useSelector((s: RootState) => s.game.currentActingPlayerId);
  const history = useSelector((s: RootState) => s.game.chatHistory);
  if (!game) return <div className="club-table-loading"><span className="club-spinner" /><p>Setting up the table…</p></div>;
  const humanIndex = Math.max(0, game.players.findIndex(p => p.isHuman));
  const showCards = game.phase === GamePhase.SHOWDOWN || game.phase === GamePhase.ENDED;
  return <div className={`club-table-stage seats-${game.players.length}`}><div className="club-table-rail"><div className="club-table-felt" /></div><CommunityCards cards={game.communityCards || []} pot={game.pot} phase={game.phase} streetBet={game.streetBet} />
    {game.players.map((player, index) => {
      const seat = (index - humanIndex + game.players.length) % game.players.length;
      const radians = (90 + seat * 360 / game.players.length) * Math.PI / 180;
      const last = [...history].reverse().find(message => message.sender === player.id && message.type === 'action');
      const action = last?.message.match(/【([^】]+)】/)?.[1];
      return <div key={player.id} className="club-seat-position" style={{ left: `${50 + 40 * Math.cos(radians)}%`, top: `${49 + 38 * Math.sin(radians)}%` }}><PlayerSeat player={player} isActing={acting === player.id} isDealer={index === game.dealerIndex} isShowdown={showCards} lastAction={action} tone={index} /></div>;
    })}
  </div>;
};
