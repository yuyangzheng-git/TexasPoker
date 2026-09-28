"""
Monte Carlo 股似率计算
并行计算 5000 次模拟，估算手牌胜率
"""
import random
from typing import List, Tuple
from hand_evaluator import Card, HandEvaluator


class MonteCarloEquityCalculator:
    """Monte Carlo 方法计算股似率"""

    @staticmethod
    def build_remaining_deck(known_cards: List[Card]) -> List[Card]:
        """构建除去已知牌后的剩余牌堆

        Card 实现了基于 (rank, suit) 的 __eq__/__hash__，
        保证已知牌（手牌 + 公共牌）不会再次出现在剩余牌堆中。
        """
        known = set(known_cards)
        remaining = [
            Card(rank, suit)
            for rank in range(2, 15)
            for suit in range(4)
            if Card(rank, suit) not in known
        ]
        assert len(remaining) == 52 - len(known), (
            f"剩余牌堆数量错误: {len(remaining)} != {52 - len(known)}"
        )
        return remaining

    @staticmethod
    def calculate_equity(
        my_hole_cards: List[Card],
        community_cards: List[Card],
        num_opponents: int,
        simulations: int = 5000
    ) -> float:
        """
        计算当前手牌的股似率（胜率）

        Args:
            my_hole_cards: 我的2张手牌
            community_cards: 当前公共牌 (0-5张)
            num_opponents: 对手数量
            simulations: 模拟次数

        Returns:
            float: 胜率 (0.0 - 1.0)
        """
        remaining_deck = MonteCarloEquityCalculator.build_remaining_deck(
            my_hole_cards + community_cards
        )

        my_wins = 0.0

        for _ in range(simulations):
            # 1. 随机补全公共牌（如果不足5张）
            shuffled = random.sample(remaining_deck, len(remaining_deck))
            simulated_community = list(community_cards)
            offset = 0

            cards_needed = 5 - len(community_cards)
            simulated_community.extend(shuffled[offset:offset + cards_needed])
            offset += cards_needed

            # 2. 随机给每个对手发2张手牌
            opponent_hands = []
            for _ in range(num_opponents):
                opponent_hands.append([
                    shuffled[offset],
                    shuffled[offset + 1]
                ])
                offset += 2

            # 3. 评估所有人的最强手牌
            my_score, _ = HandEvaluator.evaluate_best_hand(my_hole_cards, simulated_community)

            opponent_scores = []
            for opp_hand in opponent_hands:
                opp_score, _ = HandEvaluator.evaluate_best_hand(opp_hand, simulated_community)
                opponent_scores.append(opp_score)

            # 4. 统计我的胜负
            max_opp_score = max(opponent_scores) if opponent_scores else 0

            if my_score > max_opp_score:
                my_wins += 1.0
            elif my_score == max_opp_score:
                # 平局：均分给所有平手的玩家
                num_winners = 1 + sum(1 for s in opponent_scores if s == my_score)
                my_wins += 1.0 / num_winners

        return my_wins / simulations

    @staticmethod
    def calculate_equity_range(
        my_hole_cards: List[Card],
        community_cards: List[Card],
        opponent_ranges: List[Tuple[int, int]],  # 对手可能的手牌范围
        simulations: int = 5000
    ) -> float:
        """
        更高级版本：考虑对手的手牌范围（Range）
        这里简化实现，直接用对手数量
        """
        num_opponents = len(opponent_ranges)
        return MonteCarloEquityCalculator.calculate_equity(
            my_hole_cards,
            community_cards,
            num_opponents,
            simulations
        )


# WebWorker 专用：单线程批量计算（前端可用）
class BatchEquityCalculator:
    """批量计算多个牌局的股似率"""

    @staticmethod
    def batch_calculate(
        tasks: List[dict],
        simulations_per_task: int = 1000
    ) -> List[float]:
        """
        批量计算多个任务
        每个任务格式: {
            'my_hole_cards': [...],
            'community_cards': [...],
            'num_opponents': int
        }
        """
        results = []
        for task in tasks:
            equity = MonteCarloEquityCalculator.calculate_equity(
                task['my_hole_cards'],
                task['community_cards'],
                task['num_opponents'],
                simulations_per_task
            )
            results.append(equity)
        return results


# 示例使用
if __name__ == "__main__":
    # 测试：AK vs 未知对手 Preflop
    my_cards = [Card(14, 0), Card(13, 0)]  # AK♠
    community = []
    opponents = 2

    equity = MonteCarloEquityCalculator.calculate_equity(
        my_cards,
        community,
        opponents,
        simulations=1000  # 快速测试用1000次
    )

    print(f"My AK equity vs 2 opponents: {equity:.1%}")
    # 预期结果: 约 30-35% (因为在3人底池中)
