export const MAX_PLAYER_NAME = 16;

// Mirrors the server: plain text only, no control/format characters or markup brackets.
export const cleanPlayerName = (value: string) =>
  value.normalize('NFKC').replace(/[\p{C}<>]/gu, '').replace(/\s+/g, ' ').trim();
