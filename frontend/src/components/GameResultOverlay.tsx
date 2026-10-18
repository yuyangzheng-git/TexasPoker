import React, { useEffect, useState } from 'react';
import { Allocation } from '../types/game';
import { Icon, chips } from './club/Club';
interface GameResultOverlayProps { visible: boolean; finished?: boolean; allocations: Allocation[]; playerName: string; onContinue?: () => void; onReview?: () => void; disabled?: boolean }
export const GameResultOverlay: React.FC<GameResultOverlayProps> = ({ visible, finished = false, allocations, onContinue, onReview, disabled }) => {
  const [expanded, setExpanded] = useState(false); const [pending, setPending] = useState(false);
  useEffect(() => { setPending(false); setExpanded(false); }, [allocations, visible, finished]);
  if (!visible) return null;
  const mine = allocations.find(a => a.playerId === 'player_human'); const net = mine?.stackChange || 0;
  const winners = allocations.filter(a => a.amount > 0 && a.stackChange > 0);
  return <section className="club-result" aria-label="本手结算"><div className="club-result-summary"><span className="club-result-mark">{net > 0 ? '♠' : '◇'}</span><div><span className="club-eyebrow">{finished ? 'SESSION COMPLETE' : 'HAND COMPLETE'}</span><h2>{finished ? '这一场，告一段落。' : net > 0 ? '漂亮的一手。' : net === 0 ? '平稳收官。' : '下一手，新的机会。'}</h2><p>{winners.map(a => a.playerName || a.playerId).join('、') || '本手'}{winners.length ? '赢得底池' : '已结算'}<span>你的净变化 <strong className={net >= 0 ? 'club-positive' : 'club-negative'}>{net > 0 ? '+' : ''}{chips(net)}</strong></span></p></div><button className="club-btn club-btn-gold" disabled={pending || disabled} onClick={() => { setPending(true); onContinue?.(); }}>{finished ? '返回大厅' : pending ? '正在发牌…' : '开始下一手'}<Icon name="arrow" /></button></div><div className="club-result-tools"><button onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>结算明细<Icon name="chevron" /></button><button onClick={onReview}><Icon name="history" />查看赛后复盘</button></div>{expanded && <div className="club-settlement">{allocations.map(a => <div key={a.playerId}><span>{a.playerName || a.playerId}<small>{a.handRank || (a.reason === 'last_standing' ? '其他玩家弃牌' : '')}</small></span><strong className={a.stackChange > 0 ? 'club-positive' : a.stackChange < 0 ? 'club-negative' : ''}>{a.stackChange > 0 ? '+' : ''}{chips(a.stackChange)}</strong></div>)}</div>}</section>;
};
