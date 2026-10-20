import { potRaiseTo } from './raise';

test('pot fractions with nothing to call are fractions of the pot', () => {
  expect(potRaiseTo(0.5, 600, 0, 100, 10000)).toBe(300);
  expect(potRaiseTo(1, 600, 0, 100, 10000)).toBe(600);
  expect(potRaiseTo(2, 600, 0, 100, 10000)).toBe(1200);
});

test('facing a bet, a pot-sized raise counts the call first', () => {
  // Pre-flop: blinds 50/100 in the pot, 100 to call.
  expect(potRaiseTo(1, 150, 100, 200, 10000)).toBe(350);
  expect(potRaiseTo(0.5, 150, 100, 200, 10000)).toBe(225);
  expect(potRaiseTo(2, 150, 100, 200, 10000)).toBe(600);
});

test('results stay inside the legal raise range', () => {
  expect(potRaiseTo(0.5, 100, 0, 200, 10000)).toBe(200);
  expect(potRaiseTo(2, 9000, 3000, 6000, 8000)).toBe(8000);
});
