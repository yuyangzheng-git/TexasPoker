import React, { useEffect, useState } from 'react';
import { Allocation } from '../types/game';
import { Icon, Zh, chips, handRankName } from './club/Club';
import { displayName } from './club/agents';
interface GameResultOverlayProps { visible: boolean; finished?: boolean; allocations: Allocation[]; playerName: string; onContinue?: () => void; onReview?: () => void; disabled?: boolean; busted?: boolean }
export const GameResultOverlay: React.FC<GameResultOverlayProps> = ({ visible, finished = false, allocations, onContinue, onReview, disabled, busted = false }) => {
  const [expanded, setExpanded] = useState(false); const [pending, setPending] = useState(false);
  useEffect(() => { setPending(false); setExpanded(false); }, [allocations, visible, finished]);
  if (!visible) return null;
  const mine = allocations.find(a => a.playerId === 'player_human'); const net = mine?.stackChange || 0;
  const winners = allocations.filter(a => a.amount > 0 && a.stackChange > 0);
  const eyebrow = !finished ? 'HAND COMPLETE' : busted ? 'GAME OVER' : 'TABLE CLEARED';
  const [headline, headlineZh] = !finished ? (net > 0 ? ['Nicely played.', '漂亮的一手。'] : net === 0 ? ['Steady finish.', '平稳收官。'] : ['Next hand, new chance.', '下一手，新的机会。']) : busted ? ['Out of chips — game over.', '筹码已输光，本场结束。'] : ['Every chip at the table is yours.', '全场筹码尽归你手。'];
  const nameOf = (a: Allocation) => a.playerId === 'player_human' ? 'You' : displayName(a.playerId, a.playerName || a.playerId);
  return <section className="club-result" aria-label="Hand result"><div className="club-result-summary"><span className={`club-result-mark ${finished ? (busted ? 'is-out' : 'is-champion') : ''}`}>{finished ? (busted ? '◇' : '♛') : net > 0 ? '♠' : '◇'}</span><div><span className="club-eyebrow">{eyebrow}</span><h2>{headline}<Zh>{headlineZh}</Zh></h2><p>{winners.length ? `${winners.map(nameOf).join(', ')} ${winners.length === 1 && winners[0].playerId !== 'player_human' ? 'wins' : 'win'} the pot` : 'Hand settled'}<span>Your net change <strong className={net >= 0 ? 'club-positive' : 'club-negative'}>{net > 0 ? '+' : ''}{chips(net)}</strong></span></p></div><button className="club-btn club-btn-gold" disabled={pending || disabled} onClick={() => { setPending(true); onContinue?.(); }}>{finished ? (busted ? <>Back to lobby — play again<Zh>返回大厅</Zh></> : <>Back to lobby<Zh>返回大厅</Zh></>) : pending ? 'Dealing…' : <>Next hand<Zh>开始下一手</Zh></>}<Icon name="arrow" /></button></div><div className="club-result-tools"><button onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>Settlement details<Icon name="chevron" /></button><button onClick={onReview}><Icon name="history" />Review the hand</button></div>{expanded && <div className="club-settlement">{allocations.map(a => <div key={a.playerId}><span>{nameOf(a)}<small>{a.handRank ? <>{handRankName[a.handRank] || a.handRank}<Zh inline>{a.handRank}</Zh></> : a.reason === 'last_standing' ? 'Everyone else folded' : ''}</small></span><strong className={a.stackChange > 0 ? 'club-positive' : a.stackChange < 0 ? 'club-negative' : ''}>{a.stackChange > 0 ? '+' : ''}{chips(a.stackChange)}</strong></div>)}</div>}</section>;
};
