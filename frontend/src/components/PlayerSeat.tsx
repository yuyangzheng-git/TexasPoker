import React from 'react';
import { Player, PlayerStatus } from '../types/game';
import { Card } from './Card';
import { chips } from './club/Club';
import { agentInfo } from './club/agents';
interface PlayerSeatProps { player: Player; isShowdown?: boolean; isActing?: boolean; isDealer?: boolean; lastAction?: string; tone?: number }
const PlayerSeat: React.FC<PlayerSeatProps> = ({ player, isShowdown = false, isActing = false, isDealer = false, lastAction, tone = 0 }) => {
  const folded = player.status === PlayerStatus.FOLDED;
  const hasCards = !!player.holeCards?.length;
  const agent = agentInfo(player.id); const name = agent?.name || player.name;
  return <div className={`club-seat ${player.isHuman ? 'is-you' : ''} ${folded ? 'is-folded' : ''} ${isActing ? 'is-acting' : ''}`} aria-label={`${name}, ${chips(player.stack)} chips${isActing ? ', acting' : ''}${folded ? ', folded' : ''}`}>
    <div className="club-seat-cards">{hasCards ? player.holeCards?.map((card, i) => <Card key={i} rank={card.rank} suit={card.suit} small faceDown={!player.isHuman && (!isShowdown || folded)} />) : !folded && <><Card faceDown small /><Card faceDown small /></>}</div>
    <div className="club-seat-body"><span className={`club-avatar avatar-tone-${tone % 4}`}>{player.isHuman ? 'You' : name.slice(0, 1)}</span><div className="club-seat-label"><strong title={agent ? `${agent.name} · ${agent.zh}` : name}>{name}{player.isHuman && <small>you</small>}</strong><span className="club-seat-stack">{chips(player.stack)}</span></div>{isDealer && <span className="club-dealer" title="Dealer">D</span>}</div>
    <div className="club-seat-status">{isActing ? <span className="club-seat-turn">{player.isHuman ? 'Your turn' : 'Thinking'}</span> : player.status === PlayerStatus.ALLIN ? <span className="club-seat-allin">All-in</span> : folded ? <span>Folded</span> : <span>{lastAction || player.position}</span>}{player.currentBet > 0 && <span className="club-seat-bet">{chips(player.currentBet)}</span>}</div>
  </div>;
};
export default PlayerSeat;
