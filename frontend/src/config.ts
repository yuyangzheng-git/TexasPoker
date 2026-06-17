// 服务器配置
// 生产环境使用服务器地址，开发环境使用 localhost
const isProduction = window.location.hostname !== 'localhost';

export const API_BASE_URL = isProduction
  ? `http://${window.location.hostname}:8000`
  : 'http://localhost:8000';

export const WS_BASE_URL = isProduction
  ? `ws://${window.location.hostname}:8000`
  : 'ws://localhost:8000';
