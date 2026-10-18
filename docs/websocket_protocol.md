# WebSocket 通信协议

## 创建与认证

`POST /api/games` 返回 `gameId`、`sessionToken`、`wsUrl` 和玩家列表。凭证只返回给创建者，后续不会放入牌局快照或连接 URL。

连接 `/ws/{gameId}` 后，10 秒内发送：

```json
{"type":"AUTH","sessionToken":"创建牌局时返回的凭证"}
```

无效凭证关闭码为 `4403`，已有连接占用牌局时为 `4409`。同一张牌桌的连接只负责收发消息，不负责重新初始化游戏。

## 服务器消息

所有消息格式为 `{"type":"事件名","data":{}}`。

| 事件 | data 主要字段 | 说明 |
| --- | --- | --- |
| `SESSION_STATE` | `state`, `paused`, `pendingAction`, `result`, `finished` | 每次认证成功后恢复当前状态 |
| `GAME_STARTED` | 牌局快照 | 第一手开始 |
| `HAND_STARTED` | `handNumber`, `gameState` | 后续手牌开始 |
| `PHASE_CHANGED` | 牌局快照 | 进入下一街或摊牌 |
| `PLAYER_ACTION_REQUEST` | `requestId`, `playerId`, `validActions`, `callAmount`, `minRaise`, `maxRaise`, `pot`, `timeLimit` | 请求人类行动；金额为本轮累计下注目标 |
| `PLAYER_ACTION` | `playerId`, `action`, `amount`, `speech`, `pot`, `stateSnapshot` | 已执行的合法行动 |
| `AGENT_THINKING_START` | `agentId` | AI 正在决策 |
| `AGENT_THINKING_END` | `agentId`, `action`, `speech` | AI 行动和公开发言 |
| `AGENT_THINKING_CHUNK` | `agentId`, `chunk` | 仅本手结束后发布思考内容 |
| `SHOWDOWN` / `GAME_ENDED` | `allocations`, `finalState`, `requestId` | 每位玩家一条结算；仍可继续时包含下一手确认编号 |
| `TOURNAMENT_ENDED` | `winner`, `finalStacks` | 整场结束，不再接受下一手确认 |
| `PAUSE_STATE` | `paused` | 服务器确认的暂停状态 |
| `ERROR` | `message` | 非法、过期指令或运行错误 |

`SESSION_STATE.pendingAction` 为 `null` 或含 `kind`（`action` / `ready`）和 `requestId` 的对象。行动请求还包含与 `PLAYER_ACTION_REQUEST` 相同的字段；重连时 `timeLimit` 是剩余毫秒数。`result` 为 `null` 或上一手完整结算。

快照包含 `phase`、`pot`、`streetBet`、`communityCards`、`dealerIndex` 和 `players`。玩家字段包含 `id`、`name`、`stack`、`currentBet`、`status`、`position`、`isHuman`、`holeCards`。未授权查看的底牌为 `[]`；服务器不会发送真实值让前端自行隐藏。

## 客户端指令

仅对当前 `requestId` 提交行动：

```json
{"type":"ACTION","requestId":"当前行动编号","action":"raise","amount":180,"speech":"我加注"}
```

`action` 支持 `fold`、`check`、`call`、`raise`、`allin`。`raise.amount` 表示本轮累计下注到多少，必须位于服务器返回的合法范围内。跟注和全押的实际扣款由服务器计算。非法指令不扣筹码，也不会重置时限。

确认下一手：

```json
{"type":"READY_FOR_NEXT_HAND","requestId":"结算返回的确认编号"}
```

暂停 / 恢复：

```json
{"type":"PAUSE"}
{"type":"RESUME"}
```

暂停在当前行动完成后生效，已经开始的人类行动仍按原截止时间执行。重连和重复提交也不会重置时限。

更多部署与生命周期说明见 [牌局机制改进说明](mechanics-upgrade.md)。
