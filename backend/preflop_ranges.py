"""
翻前起手牌强度排序与范围百分位

169 种起手牌按强度排序（离线用 fast_eval 蒙特卡洛生成：单挑胜率与对 3 个对手胜率的
z 分数各占一半，适合 6~9 人桌）。percentile(hand) 返回该手牌在全部 1326 种组合中的
累计位置（0=最强，1=最弱），范围 "前 25%" 即 percentile <= 0.25 的手牌。
"""
from typing import Dict, List, Sequence

RANK_CHARS = "23456789TJQKA"

ORDER: List[str] = [
    'AA', 'KK', 'QQ', 'JJ', 'TT', '99', 'AKs', '88', 'AQs', 'KQs', 'ATs', 'AJs', 'AQo',
    'AKo', '77', 'AJo', 'KJs', 'KTs', 'ATo', 'KQo', 'QJs', 'A9s', 'A8s', 'A7s', '66', 'KJo',
    'QTs', 'K9s', 'A5s', 'KTo', 'QJo', 'JTs', 'A4s', 'A6s', 'A9o', 'QTo', 'K8s', 'A8o',
    '55', 'A3s', 'A5o', 'Q9s', 'J9s', 'K9o', 'K7s', 'A2s', 'JTo', 'A7o', 'Q9o', 'K6s',
    'A6o', 'A4o', 'T9s', 'Q8s', 'K5s', 'J8s', 'K4s', 'K8o', '44', 'K7o', 'Q7s', 'K3s',
    'A3o', 'T8s', 'J7s', 'K2s', 'Q8o', 'J9o', '98s', 'A2o', 'Q6s', 'Q5s', 'K6o', '97s',
    'T9o', 'K5o', 'T7s', 'J8o', 'J6s', 'Q7o', 'Q4s', 'J5s', 'K4o', 'Q6o', '87s', '22',
    'T6s', 'J7o', '33', 'Q3s', 'K3o', 'T8o', 'Q4o', 'Q2s', '98o', 'J4s', 'Q5o', 'J3s',
    '86s', '96s', 'K2o', 'T7o', '76s', 'J2s', 'T5s', 'T4s', '95s', 'Q3o', 'J6o', 'T3s',
    '97o', '87o', 'J5o', '65s', 'Q2o', '85s', 'J4o', '75s', '94s', 'T2s', 'T6o', '86o',
    '54s', 'T5o', '76o', 'J3o', '93s', '96o', '84s', '74s', '82s', 'J2o', 'T4o', '64s',
    '65o', '92s', '53s', '85o', 'T2o', '95o', '63s', 'T3o', '83s', '73s', '94o', '52s',
    '75o', '54o', '84o', '74o', '62s', '72s', '92o', '42s', '43s', '64o', '32s', '93o',
    '43o', '53o', '63o', '83o', '82o', '73o', '52o', '72o', '42o', '62o', '32o'
]


def _combos(name: str) -> int:
    if len(name) == 2:
        return 6
    return 4 if name[2] == "s" else 12


def _build_percentiles() -> Dict[str, float]:
    total = 1326.0
    acc = 0.0
    out = {}
    for name in ORDER:
        c = _combos(name)
        # 取该类组合区间的中点，避免同一类手牌因位置边界被整体纳入/排除
        out[name] = (acc + c / 2.0) / total
        acc += c
    return out


PERCENTILE: Dict[str, float] = _build_percentiles()


def class_name(r1: int, s1: int, r2: int, s2: int) -> str:
    hi, lo = (r1, r2) if r1 >= r2 else (r2, r1)
    a, b = RANK_CHARS[hi - 2], RANK_CHARS[lo - 2]
    if hi == lo:
        return a + b
    return a + b + ("s" if s1 == s2 else "o")


def percentile_of_codes(c1: int, c2: int) -> float:
    return PERCENTILE[class_name(c1 >> 2, c1 & 3, c2 >> 2, c2 & 3)]


def percentile_of_cards(cards: Sequence) -> float:
    a, b = cards[0], cards[1]
    return PERCENTILE[class_name(a.rank, a.suit, b.rank, b.suit)]


def hand_features(c1: int, c2: int) -> dict:
    """翻前手牌的结构特征：对子、同花、连张程度（用于隐含赔率修正）。"""
    r1, r2 = c1 >> 2, c2 >> 2
    hi, lo = max(r1, r2), min(r1, r2)
    gap = hi - lo
    return {
        "pair": r1 == r2,
        "suited": (c1 & 3) == (c2 & 3),
        "connected": gap == 1 or (hi == 14 and lo == 2),
        "gap": gap,
        "high": hi,
    }
