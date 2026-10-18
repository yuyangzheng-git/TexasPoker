import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import gameReducer from '../store/gameSlice';
import { useWebSocket } from './useWebSocket';

class Socket {
  static OPEN = 1;
  static instances = [];
  readyState = 1;
  send = jest.fn();
  close = jest.fn();
  constructor() { Socket.instances.push(this); }
  open() { this.onopen(); }
  emit(type, data) { this.onmessage({ data: JSON.stringify({ type, data }) }); }
}

let root, container, store, controls;
const nativeSocket = global.WebSocket;
const state = { phase: 'pre_flop', pot: 150, streetBet: 100, dealerIndex: 0,
  communityCards: [], players: [{ id: 'player_human', isHuman: true, stack: 9950 }] };
function Probe() { controls = useWebSocket('table'); return null; }

beforeEach(() => {
  jest.useFakeTimers();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  global.WebSocket = Socket;
  Socket.instances = [];
  sessionStorage.setItem('poker_session_table', 'private-capability');
  store = configureStore({ reducer: { game: gameReducer },
    middleware: getDefault => getDefault({ serializableCheck: false }) });
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root.render(<Provider store={store}><Probe /></Provider>));
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  jest.clearAllTimers();
  jest.useRealTimers();
  global.WebSocket = nativeSocket;
});

test('authenticates with a frame and submits server request IDs and raise bounds', () => {
  const socket = Socket.instances[0];
  act(() => socket.open());
  expect(JSON.parse(socket.send.mock.calls[0][0])).toEqual({ type: 'AUTH', sessionToken: 'private-capability' });
  expect(store.getState().game.connected).toBe(false);
  act(() => socket.emit('SESSION_STATE', { state, paused: false, finished: false }));
  expect(store.getState().game.connected).toBe(true);
  act(() => socket.emit('PLAYER_ACTION_REQUEST', { requestId: 'turn-1', playerId: 'player_human',
    callAmount: 50, pot: 150, minRaise: 180, maxRaise: 10000,
    validActions: ['fold', 'call', 'raise', 'allin'], timeLimit: 10000 }));
  expect(store.getState().game.playerActionRequest.minRaise).toBe(180);
  act(() => controls.submitAction('player_human', 'raise', 180));
  expect(JSON.parse(socket.send.mock.calls[1][0])).toMatchObject({
    type: 'ACTION', requestId: 'turn-1', action: 'raise', amount: 180,
  });
});

test('reconnect restores the current request and cleanup cancels retries', () => {
  const first = Socket.instances[0];
  act(() => first.onclose({ code: 1006 }));
  act(() => jest.advanceTimersByTime(1500));
  const second = Socket.instances[1];
  expect(second).toBeDefined();
  act(() => first.emit('SESSION_STATE', { state: { ...state, pot: 999999 }, paused: false }));
  expect(store.getState().game.gameState).toBeUndefined();
  act(() => second.emit('SESSION_STATE', { state, paused: true, finished: false,
    pendingAction: { kind: 'action', requestId: 'resumed-turn', playerId: 'player_human',
      callAmount: 50, pot: 150, minRaise: 180, maxRaise: 10000,
      validActions: ['fold', 'call'], timeLimit: 4000 } }));
  expect(store.getState().game.isPaused).toBe(true);
  expect(store.getState().game.playerActionRequest.timeLimit).toBe(4000);
  act(() => controls.submitAction('player_human', 'call'));
  expect(JSON.parse(second.send.mock.calls[0][0]).requestId).toBe('resumed-turn');
  act(() => second.onclose({ code: 1006 }));
  act(() => root.unmount());
  root = { unmount() {} };
  act(() => jest.advanceTimersByTime(3000));
  expect(Socket.instances).toHaveLength(2);
});

test.each([4403, 4409])('authorization/conflict failure %s displays an error without retrying', code => {
  const socket = Socket.instances[0];
  act(() => socket.onclose({ code }));
  expect(store.getState().game.connectionError).toBeTruthy();
  act(() => jest.advanceTimersByTime(5000));
  expect(Socket.instances).toHaveLength(1);
});

test('replay restores settled results and readiness ID', () => {
  const socket = Socket.instances[0];
  act(() => socket.emit('SESSION_STATE', { state, paused: false, finished: false,
    result: { allocations: [], finalState: state }, pendingAction: { kind: 'ready', requestId: 'next-hand' } }));
  expect(store.getState().game.gameResult).toBeDefined();
  act(() => controls.sendMessage({ type: 'READY_FOR_NEXT_HAND' }));
  expect(JSON.parse(socket.send.mock.calls[0][0])).toEqual({ type: 'READY_FOR_NEXT_HAND', requestId: 'next-hand' });
});
