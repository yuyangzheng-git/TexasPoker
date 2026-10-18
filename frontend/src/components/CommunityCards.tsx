import React from 'react';
import { Card } from './Card';
import { GamePhase } from '../types/game';
import { chips, phaseName } from './club/Club';
interface CommunityCardsProps { cards: Array<{ rank: number; suit: number }>; pot: number; phase: GamePhase; streetBet: number }
export const CommunityCards: React.FC<CommunityCardsProps> = ({ cards, pot, phase, streetBet }) => <div className="club-community"><span className="club-table-phase">{phaseName[phase]}</span><div className="club-pot"><span>底池</span><strong>{chips(pot)}</strong></div><div className="club-board" aria-label="公共牌">{Array.from({ length: 5 }, (_, i) => cards[i] ? <Card key={`${i}-${cards[i].rank}-${cards[i].suit}`} rank={cards[i].rank} suit={cards[i].suit} animate /> : <div key={i} className="club-card-placeholder" aria-label="待发公共牌"><span>♠</span></div>)}</div>{streetBet > 0 && <span className="club-table-street">本轮最高下注 {chips(streetBet)}</span>}<span className="club-table-watermark">TEXAS POKER CLUB</span></div>;
