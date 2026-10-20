import React from 'react';
import { Card } from './Card';
import { GamePhase } from '../types/game';
import { chips, phaseName, phaseNameZh } from './club/Club';
interface CommunityCardsProps { cards: Array<{ rank: number; suit: number }>; pot: number; phase: GamePhase; streetBet: number }
export const CommunityCards: React.FC<CommunityCardsProps> = ({ cards, pot, phase, streetBet }) => <div className="club-community"><span className="club-table-phase">{phaseName[phase]}<span lang="zh-CN"> · {phaseNameZh[phase]}</span></span><div className="club-pot"><span>Pot</span><strong>{chips(pot)}</strong></div><div className="club-board" aria-label="Board">{Array.from({ length: 5 }, (_, i) => cards[i] ? <Card key={`${i}-${cards[i].rank}-${cards[i].suit}`} rank={cards[i].rank} suit={cards[i].suit} animate /> : <div key={i} className="club-card-placeholder" aria-label="Card not dealt yet"><span>♠</span></div>)}</div>{streetBet > 0 && <span className="club-table-street">Current bet {chips(streetBet)}</span>}<span className="club-table-watermark">TEXAS POKER CLUB</span></div>;
