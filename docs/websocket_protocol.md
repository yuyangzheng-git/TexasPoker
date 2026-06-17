# WebSocket 通信协议

## 连接

```
ws://localhost:8000/ws/{gameId}?playerId={playerId}
```

## 消息格式

所有消息为 JSON，结构如下：

```json
{
  "type": "EVENT_TYPE",
  "data": { ... },
  "timestamp": 1700000000000
}
```

---

## 服务器 → 客户端 事件

### GAME_STARTED
游戏开始，包含初始状态

```json
{
  "type": "GAME_STARTED",
  "data": {
    "gameId": "abc123",
    "phase": "pre_flop",
    "pot": 30,
    "streetBet": 20,
    "communityCards": [],
    "players": [
      {
        "id": "player_human",
        "name": "Alice",
        "stack": 980,
        "currentBet": 20,
        "status": "active",
        "position": "big_blind",
        "isHuman": true
      },
      {
        "id": "agent_laowang",
        "name": "老王",
        "stack": 990,
        "currentBet": 10,
        "status": "active",
        "position": "small_blind"
      }
    ]
  }
}
```

### PHASE_CHANGED
进入新的下注阶段

```json
{
  "type": "PHASE_CHANGED",
  "data": {
    "phase": "flop",
    "communityCards": [
      {"rank": 14, "suit": 0},
      {"rank": 13, "suit": 1},
      {"rank": 12, "suit": 2}
    ],
    "pot": 150,
    "streetBet": 0
  }
}
```

### AGENT_THINKING_START
Agent 开始思考（UI 显示加载动画）

```json
{
  "type": "AGENT_THINKING_START",
  "data": { "agentId": "agent_laowang" }
}
```

### AGENT_THINKING_CHUNK
Agent 思考流式输出（逐字符/逐块）

```json
{
  "type": "AGENT_THINKING_CHUNK",
  "data": {
    "agentId": "agent_laowang",
    "chunk": "我的手牌是 AK，这是很强的起手牌"
  }
}
```

### AGENT_THINKING_END
Agent 完成思考，执行行动

```json
{
  "type": "AGENT_THINKING_END",
  "data": {
    "agentId": "agent_laowang",
    "action": "raise",
    "amount": 80,
    "speech": "来玩真的。"
  }
}
```

### PLAYER_ACTION
某玩家执行了行动（广播给所有人）

```json
{
  "type": "PLAYER_ACTION",
  "data": {
    "playerId": "agent_laowang",
    "action": "raise",
    "amount": 80,
    "pot": 230,
    "playerStack": 910
  }
}
```

### PLAYER_ACTION_REQUEST
轮到真人玩家行动（UI 显示操作面板）

```json
{
  "type": "PLAYER_ACTION_REQUEST",
  "data": {
    "playerId": "player_human",
    "callAmount": 60,
    "pot": 230,
    "validActions": ["fold", "call", "raise", "allin"],
    "timeLimit": 30000
  }
}
```

### SHOWDOWN
摊牌，揭示所有手牌和赢家

```json
{
  "type": "SHOWDOWN",
  "data": {
    "allocations": [
      {
        "playerId": "agent_laowang",
        "amount": 460,
        "bestHand": [
          {"rank": 14, "suit": 0},
          {"rank": 14, "suit": 1}
        ],
        "reason": "showdown"
      }
    ],
    "finalState": { ... }
  }
}
```

### GAME_ENDED
游戏结束（只剩1人或所有手牌完成）

```json
{
  "type": "GAME_ENDED",
  "data": {
    "winner": "agent_dushen",
    "finalStacks": {
      "player_human": 0,
      "agent_dushen": 6000
    }
  }
}
```

---

## 客户端 → 服务器 事件

### submit_action
玩家提交行动

```json
{
  "playerId": "player_human",
  "action": "raise",
  "amount": 150
}
```

### chat_message
玩家发送聊天消息

```json
{
  "playerId": "player_human",
  "message": "nice hand!"
}
```

---

## 错误码

| type | 说明 |
|------|------|
| `ERROR_GAME_NOT_FOUND` | gameId 无效 |
| `ERROR_INVALID_ACTION` | 行动不合法 |
| `ERROR_NOT_YOUR_TURN` | 未轮到该玩家 |
| `ERROR_TIMEOUT` | 操作超时 |
