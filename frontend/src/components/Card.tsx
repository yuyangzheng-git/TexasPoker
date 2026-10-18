import React from 'react';
interface CardProps { rank?: number; suit?: number; faceDown?: boolean; animate?: boolean; small?: boolean }
const ranks: Record<number, string> = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' };
const suits = ['♠', '♥', '♦', '♣'];
const suitNames = ['黑桃', '红桃', '方块', '梅花'];
export const Card: React.FC<CardProps> = ({ rank = 14, suit = 0, faceDown = false, animate = false, small = false }) => {
  if (faceDown) return <div className={`club-card is-back ${small ? 'is-small' : ''}`} aria-label="未公开的底牌"><span>♠</span></div>;
  return <div className={`club-card suit-${suit} ${small ? 'is-small' : ''} ${animate ? 'is-dealt' : ''}`} aria-label={`${suitNames[suit]} ${ranks[rank] || rank}`}><span className="club-card-corner">{ranks[rank] || rank}<small>{suits[suit]}</small></span><span className="club-card-center" aria-hidden="true">{suits[suit]}</span><span className="club-card-corner is-bottom" aria-hidden="true">{ranks[rank] || rank}<small>{suits[suit]}</small></span></div>;
};
