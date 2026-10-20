// Raise-to total for a pot-fraction bet. Facing a bet, "pot" means the pot after
// calling, so a pot-sized raise is call + (pot + call); with nothing to call it is
// simply fraction × pot. The result is clamped into the legal raise range.
export function potRaiseTo(fraction: number, pot: number, callAmount: number, minRaise: number, maxRaise: number): number {
  const target = callAmount + fraction * (pot + callAmount);
  return Math.min(maxRaise, Math.max(minRaise, Math.round(target)));
}
