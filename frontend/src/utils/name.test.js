import { cleanPlayerName } from './name';

test('player names are reduced to plain single-spaced text', () => {
  expect(cleanPlayerName('  <b>小​明</b>\n  牌手 ')).toBe('b小明/b 牌手');
  expect(cleanPlayerName('<>​ ')).toBe('');
});
