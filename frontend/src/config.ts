// Override REACT_APP_API_URL for a separate API host; otherwise use a same-origin
// reverse proxy in production and port 8000 during local development.
const local = process.env.NODE_ENV === 'development' &&
  ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
export const API_BASE_URL = (process.env.REACT_APP_API_URL || (
  local ? `${window.location.protocol}//${window.location.hostname}:8000` : window.location.origin
)).replace(/\/$/, '');
export const WS_BASE_URL = API_BASE_URL.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
