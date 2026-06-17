# 底池赔率计算

## 公式

```
Pot Odds = Call Amount / (Pot + Call Amount)

期望值 (EV) = Equity × Pot - (1 - Equity) × Call Amount

决策规则：
  if Equity > Pot Odds → 正期望值，应该跟注 ✓
  else → 负期望值，应该弃牌 ✗
```

## 例子

**场景**：底池 $100，需要跟注 $20

```
Pot Odds = 20 / (100 + 20) = 0.167 = 16.7%
保本所需胜率 = 16.7%

我的手牌股似率 = 25%
期望值 = 0.25 × 100 - 0.75 × 20 = $25 - $15 = +$10 ✓
```

## 隐含赔率 (Implied Odds)
考虑后续轮次的潜在赢利，激进跟注者可以降低立即需要的胜率。

## 代码实现
见 `backend/agent_engine.py:calculate_pot_odds()`
