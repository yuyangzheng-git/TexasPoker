import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GameResultOverlay } from './GameResultOverlay';

let container, root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

const allocations = [
  { playerId: 'player_human', playerName: '你', amount: 0, stackChange: -500, reason: 'no_win' },
  { playerId: 'agent_laowang', playerName: '老王', amount: 1000, stackChange: 500, reason: 'showdown' },
];
const render = props => act(() => root.render(<GameResultOverlay visible allocations={allocations} playerName="你" {...props} />));

test('a busted human sees a game-over state with a way back to the lobby', () => {
  render({ finished: true, busted: true });
  expect(container.textContent).toContain('GAME OVER');
  expect(container.textContent).toContain('Out of chips');
  expect(container.querySelector('h2 .club-zh').textContent).toBe('筹码已输光，本场结束。');
  expect(container.querySelector('.club-btn-gold').textContent).toContain('Back to lobby');
  expect(container.querySelector('.club-result-mark').className).toContain('is-out');
});

test('a human who clears the table sees the champion state', () => {
  render({ finished: true, busted: false });
  expect(container.textContent).toContain('TABLE CLEARED');
  expect(container.querySelector('.club-result-mark').className).toContain('is-champion');
});

test('between hands the result offers the next hand', () => {
  render({ finished: false });
  expect(container.textContent).toContain('HAND COMPLETE');
  expect(container.querySelector('.club-btn-gold').textContent).toContain('Next hand');
});

test('AI winners are shown by their English name', () => {
  render({ finished: false });
  expect(container.textContent).toContain('Wang wins the pot');
  expect(container.textContent).not.toContain('老王');
});
