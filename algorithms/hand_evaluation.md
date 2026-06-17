# 手牌评估算法

## 目标
从 7 张牌找出最强 5 张组合。

## 核心算法：C(7,5) 枚举

```
for each combo of choose(7cards, 5):
    rank = classify_5_cards(combo)
    if rank > best_rank:
        best = combo
return best
```

**时间复杂度**：O(C(7,5)) = O(21) = O(1)

## 牌型分类（从高到低）

| 牌型 | 分值 | 例子 |
|------|------|------|
| 皇家同花顺 | 9000 | A♠K♠Q♠J♠T♠ |
| 同花顺 | 8000+ | 9♥8♥7♥6♥5♥ |
| 四条 | 7000+ | 8♠8♥8♦8♣ + kicker |
| 葫芦 | 6000+ | 9♠9♥9♦4♠4♥ |
| 同花 | 5000+ | A♠K♠J♠9♠5♠ |
| 顺子 | 4000+ | 9♠8♥7♦6♣5♠ |
| 三条 | 3000+ | 7♠7♥7♦K♠Q♥ |
| 两对 | 2000+ | K♠K♥8♦8♣3♠ |
| 一对 | 1000+ | J♠J♥9♦6♣2♠ |
| 高牌 | 0+ | A♠K♥Q♦J♣9♠ |

## 特殊情况

### 轮子顺 (Wheel)
A-2-3-4-5 是最低顺子，在此组合中 5 为最高牌。

```python
if sorted_ranks == [14, 5, 4, 3, 2]:
    return True, 5  # 轮子，5最高
```

### Kicker 破平
同牌型的手牌用 kicker（辅助牌）决出高低。

## 代码实现
见 `backend/hand_evaluator.py:HandEvaluator.evaluate_5_cards()`
