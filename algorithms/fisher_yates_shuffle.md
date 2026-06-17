# Fisher-Yates 洗牌算法

## 目标
在 O(n) 时间内生成均匀随机排列。

## 算法

```
for i from deck.length - 1 downTo 1:
    j = random(0, i)
    swap(deck[i], deck[j])
```

## 关键点
- **密码学随机数**：使用 `crypto.getRandomValues()` 保证安全
- **时间复杂度**：O(n)
- **空间复杂度**：O(1) in-place

## 应用
- 发牌前：洗完整 52 张牌组
- MC 模拟中：洗剩余牌组，样本对手手牌

## 代码实现
见 `backend/hand_evaluator.py:_shuffle_deck()`
