# Texas Hold'em Poker - LLM Agent Frontend

A modern React + TypeScript frontend for a multiplayer Texas Hold'em Poker game powered by LLM agents.

## Features

- **Real-time WebSocket communication** with Socket.io for live game updates
- **Redux Toolkit state management** for predictable state handling
- **Responsive poker table UI** with player seats distributed around an oval table
- **AI agent thinking panel** that streams LLM reasoning tokens in real-time
- **Action panel** with fold/call/raise/all-in controls
- **Dark poker theme** using Tailwind CSS with custom poker colors
- **Smooth animations** with Framer Motion
- **Game lobby** for configuring games with custom settings

## Project Structure

```
frontend/
├── src/
│   ├── types/
│   │   └── game.ts              # TypeScript interfaces for game logic
│   ├── store/
│   │   ├── gameSlice.ts         # Redux state management & reducers
│   │   └── index.ts             # Redux store configuration
│   ├── hooks/
│   │   └── useWebSocket.ts      # WebSocket hook with event handling
│   ├── components/
│   │   ├── Card.tsx             # Playing card component with animations
│   │   ├── PlayerSeat.tsx       # Individual player seat with status
│   │   ├── PokerTable.tsx       # Main oval poker table layout
│   │   ├── CommunityCards.tsx   # Flop/Turn/River display
│   │   ├── ActionPanel.tsx      # Player controls (Fold/Call/Raise)
│   │   └── AgentThinkingPanel.tsx # LLM thinking stream display
│   ├── pages/
│   │   ├── LobbyPage.tsx        # Game setup & configuration
│   │   └── GamePage.tsx         # Main game view with all panels
│   ├── App.tsx                  # Router setup
│   ├── index.tsx                # React entry point
│   └── index.css                # Global Tailwind styles
├── index.html                   # HTML entry point
├── package.json                 # Dependencies
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite build configuration
├── tailwind.config.js           # Tailwind dark poker theme
└── .env.example                 # Environment variables template
```

## Installation

```bash
cd frontend
npm install
```

## Environment Setup

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

Update the `VITE_WS_URL` if your backend server runs on a different port:

```
VITE_WS_URL=http://localhost:5000
```

## Development

Start the dev server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

Build for production:

```bash
npm run build
npm run preview
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run type-check` - Check TypeScript types
- `npm run lint` - Run ESLint

## Key Technologies

- **React 18** - UI library
- **TypeScript** - Type-safe development
- **Redux Toolkit** - State management
- **Socket.io** - Real-time WebSocket communication
- **Framer Motion** - Animation library
- **Tailwind CSS** - Utility-first styling
- **Vite** - Lightning-fast build tool

## Game State Architecture

### Redux Store Structure

```typescript
{
  game: {
    game: GameState | null,              // Current game state
    config: GameConfig | null,           // Game configuration
    currentPlayerId: string | null,      // Current player's ID
    gameLog: string[],                   // Game action log
    ui: {
      isConnected: boolean,              // WebSocket connection status
      isConnecting: boolean,
      connectionError: string | null,
      isLoading: boolean,
      activeThinking: AgentThinking | null, // Currently thinking agent
      thinkingHistory: AgentThinking[],  // Recent agent decisions
      selectedRaise: number,             // Raise amount selector
      notification: Notification | null, // Toast notifications
      showCards: boolean,                // Show/hide hole cards
      lastAction: PlayerAction | null,   // Last action for animation
    }
  }
}
```

### WebSocket Events

#### Server → Client

- `game_state` - Full game state update
- `phase_change` - Game phase changed (preflop/flop/turn/river)
- `player_update` - Individual player state update
- `pot_update` - Pot size updated
- `player_action` - Player made an action
- `agent_thinking_start` - Agent started thinking
- `agent_thinking_token` - Streaming LLM token
- `agent_thinking_complete` - Agent decision finalized
- `hand_complete` - Hand winner announced
- `game_over` - Game ended
- `error` - Error message

#### Client → Server

- `join_game` - Join a game session
- `start_game` - Start a new game with config
- `player_action` - Submit player action
- `request_game_state` - Request full game state

## UI Components

### Card Component
Renders individual playing cards with suit and rank. Supports face-down state and animations.

### PlayerSeat Component
Displays a player's position with avatar, stack, hole cards, and action indicators.

### PokerTable Component
Main container that positions player seats around an oval table and displays community cards.

### ActionPanel Component
Provides fold/check/call/raise/all-in controls with customizable raise amounts.

### AgentThinkingPanel Component
Real-time display of LLM agent reasoning with collapsible history.

### CommunityCards Component
Shows the flop (3 cards), turn (1 card), and river (1 card) with phase indicator.

## Styling

The project uses a custom dark poker theme with:

- **Primary colors**: Dark greens and blacks for the felt table
- **Accent colors**: Gold chips, red/blue/black suit colors
- **Custom animations**: Chip drops, card flips, pulse glows
- **Responsive layout**: Works on desktop with potential for mobile adaptation

## Type Definitions

All game types are defined in `src/types/game.ts`:

- `Card` - Playing card with suit and rank
- `PlayerState` - Individual player information
- `GamePhase` - Game phase with community cards and pot
- `GameState` - Complete game state
- `AgentThinking` - LLM agent's thinking process
- `PlayerAction` - Action taken by a player
- `GameConfig` - Game configuration settings

## WebSocket Hook

The `useWebSocket` hook manages all WebSocket communication:

```typescript
const { socket, connect, disconnect, sendAction, joinGame, startGame } = useWebSocket(gameId);
```

Automatically:
- Connects/disconnects with the server
- Handles reconnection logic
- Dispatches Redux actions for state updates
- Manages loading states and notifications

## Future Enhancements

- Mobile responsive design
- Player authentication & profiles
- Game replay system
- Hand history database
- Statistics tracking
- Different AI difficulty levels
- Chat system
- Tournament mode
- Spectator mode
