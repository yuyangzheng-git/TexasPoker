import React from 'react';
import { Player, PlayerStatus } from '../types/game';
import { Card } from './Card';
import { chips } from './club/Club';
interface PlayerSeatProps { player: Player; isShowdown?: boolean; isActing?: boolean; isDealer?: boolean; lastAction?: string; tone?: number }
const PlayerSeat: React.FC<PlayerSeatProps> = ({ player, isShowdown = false, isActing = false, isDealer = false, lastAction, tone = 0 }) => {
  const folded = player.status === PlayerStatus.FOLDED;
  const hasCards = !!player.holeCards?.length;
  return <div className={`club-seat ${player.isHuman ? 'is-you' : ''} ${folded ? 'is-folded' : ''} ${isActing ? 'is-acting' : ''}`} aria-label={`${player.name}，筹码 ${chips(player.stack)}${isActing ? '，正在行动' : ''}${folded ? '，已弃牌' : ''}`}>
    <div className="club-seat-cards">{hasCards ? player.holeCards?.map((card, i) => <Card key={i} rank={card.rank} suit={card.suit} small faceDown={!player.isHuman && (!isShowdown || folded)} />) : !folded && <><Card faceDown small /><Card faceDown small /></>}</div>
    <div className="club-seat-body"><span className={`club-avatar avatar-tone-${tone % 4}`}>{player.isHuman ? '你' : player.name.slice(0, 1)}</span><div className="club-seat-label"><strong title={player.name}>{player.name}{player.isHuman && <small>你</small>}</strong><span className="club-seat-stack">{chips(player.stack)}</span></div>{isDealer && <span className="club-dealer" title="庄家">D</span>}</div>
    <div className="club-seat-status">{isActing ? <span className="club-seat-turn">{player.isHuman ? '轮到你' : '思考中'}</span> : player.status === PlayerStatus.ALLIN ? <span className="club-seat-allin">全押</span> : folded ? <span>已弃牌</span> : <span>{lastAction || player.position}</span>}{player.currentBet > 0 && <span className="club-seat-bet">{chips(player.currentBet)}</span>}</div>
  </div>;
};
export default PlayerSeat;
