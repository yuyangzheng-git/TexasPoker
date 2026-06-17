# 对手行为分析

## 统计指标

| 指标 | 含义 | 范围 | 解读 |
|------|------|------|------|
| VPIP | 主动投入底池率 | 0-100% | VPIP > 40% = 激进 |
| PFR | 翻牌前加注率 | 0-100% | PFR / VPIP = 加注/跟注比例 |
| Aggression | 激进系数 | 0-∞ | raise / call 比例 |
| Bluff Freq | 虚张声势率 | 0-100% | 下注时手牌弱的百分比 |
| Fold to Bet | 对下注的弃牌率 | 0-100% | 高 = 容易被施压 |

## 实现

```python
class OpponentProfile:
    hands_observed: int          # 观察的手数
    vpip: float                  # 滑动平均
    pfr: float
    recent_actions: List[Action] # 最近20手记录

    def update(action_type, context):
        # 增量更新统计
        vpip = (vpip * old_count + new_sample) / new_count
```

## 利用对手画像

Agent Prompt 会接收到对手分析：
```
【对手分析】
[Alice] 激进型 | VPIP 45% | 近期: raise → call → fold
[Bob]   保守型 | VPIP 20% | 近期: fold → check → fold
```

## 代码实现
见 `backend/agent_engine.py:OpponentProfile`
