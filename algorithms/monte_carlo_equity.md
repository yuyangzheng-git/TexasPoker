# Monte Carlo 胜率计算

## 目标
快速估算当前手牌的胜率（equity）。

## 算法

```
wins = 0
for simulation in range(5000):
    1. 补全公共牌（随机补到5张）
    2. 随机生成所有对手的手牌
    3. 比较所有玩家的最强手牌
    4. 如果我赢，wins++
    5. 如果平，wins += 0.5

return wins / 5000  # 胜率 0.0-1.0
```

## 性能优化

### 1. WebWorker 并行化（前端）
```javascript
WORKER_COUNT = CPU核心数
SIMS_PER_WORKER = 5000 / WORKER_COUNT
// 每个 worker 运行 1250 次模拟
// 合并结果 → 总胜率
```

### 2. 查表法（Pre-flop）
```
PREFLOP_TABLE = {
  "AKs": 0.63,
  "AKo": 0.58,
  "AA": 0.85,
  ...
}
```

### 3. LRU 缓存
```
CACHE[key] = (hole_cards, community, opponents) → equity
```

## 时间要求
- **目标**：5000 次模拟 < 100ms
- **4核 CPU**：~25ms （4 个 worker 并行）

## 代码实现
见 `backend/monte_carlo_equity.py:MonteCarloEquityCalculator`
