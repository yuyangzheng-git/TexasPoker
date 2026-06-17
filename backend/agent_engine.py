"""
LLM Agent 引擎
负责 Prompt 构建、LLM 调用、响应解析和记忆管理
"""
import re
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable

from game_engine import GameEngine, Player, Action, ActionType
from monte_carlo_equity import MonteCarloEquityCalculator


# 加载全局配置
with open("../config/game_config.json") as _f:
    _game_cfg = json.load(_f)
MC_SIMULATIONS = _game_cfg.get("monte_carlo", {}).get("simulations", 5000)


# ──────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────

@dataclass
class OpponentProfile:
    player_id: str
    hands_observed: int = 0
    vpip: float = 0.0          # 主动投入底池率
    pfr: float = 0.0           # 翻牌前加注率
    aggression: float = 0.0    # 激进系数
    bluff_frequency: float = 0.0
    fold_to_bet: float = 0.0
    recent_actions: list = field(default_factory=list)

    def update(self, action_type: str, context: dict):
        self.hands_observed += 1
        if action_type in ["call", "raise", "allin"]:
            self.vpip = (self.vpip * (self.hands_observed - 1) + 1) / self.hands_observed
        if action_type == "raise":
            self.pfr = (self.pfr * (self.hands_observed - 1) + 1) / self.hands_observed
        if action_type == "fold" and context.get("facing_bet"):
            self.fold_to_bet = (self.fold_to_bet * (self.hands_observed - 1) + 1) / self.hands_observed

        self.recent_actions.append({"action": action_type, "phase": context.get("phase", "")})
        if len(self.recent_actions) > 20:
            self.recent_actions.pop(0)


@dataclass
class AgentMemory:
    hands_played: int = 0
    win_rate: float = 0.0
    cumulative_winnings: float = 0.0
    opponent_profiles: dict = field(default_factory=dict)
    recent_results: list = field(default_factory=list)
    seasonal_meta: list = field(default_factory=list)

    def record_result(self, won: bool, amount: float):
        self.hands_played += 1
        if won:
            self.cumulative_winnings += amount
        result = "W" if won else "L"
        self.recent_results.append(result)
        if len(self.recent_results) > 10:
            self.recent_results.pop(0)
        self.win_rate = self.recent_results.count("W") / len(self.recent_results)

    def get_opponent_profile(self, player_id: str) -> OpponentProfile:
        if player_id not in self.opponent_profiles:
            self.opponent_profiles[player_id] = OpponentProfile(player_id=player_id)
        return self.opponent_profiles[player_id]

    def get_prompt_summary(self) -> str:
        return (
            f"总手数: {self.hands_played}, "
            f"近期胜率: {self.win_rate:.0%}, "
            f"累计盈亏: ${self.cumulative_winnings:+.0f}, "
            f"近期: {' '.join(self.recent_results)}"
        )


@dataclass
class ParsedResponse:
    thinking: str = ""
    action: Optional[Action] = None
    speech: str = ""


# ──────────────────────────────────────────
# 底池赔率计算
# ──────────────────────────────────────────

def calculate_pot_odds(pot: float, call_amount: float) -> dict:
    if call_amount <= 0:
        return {"pot_odds": 0.0, "break_even_equity": 0.0}
    pot_odds = call_amount / (pot + call_amount)
    return {
        "pot_odds": pot_odds,
        "break_even_equity": pot_odds,
    }


def calculate_ev(equity: float, pot: float, call_amount: float) -> float:
    return equity * pot - (1 - equity) * call_amount


# ──────────────────────────────────────────
# Prompt 构建器
# ──────────────────────────────────────────

def evaluate_preflop_hand(hole_cards) -> tuple:
    """
    评估翻牌前起手牌强度
    返回 (等级, 描述, 建议行动)
    等级: 1=超强, 2=强牌, 3=中等, 4=可玩, 5=投机, 6=弱牌
    """
    if len(hole_cards) != 2:
        return (6, "未知", "谨慎行动")

    r1, r2 = hole_cards[0].rank, hole_cards[1].rank
    s1, s2 = hole_cards[0].suit, hole_cards[1].suit

    # 标准化：大牌在前
    high, low = max(r1, r2), min(r1, r2)
    # A 用 14 表示
    if high == 1: high = 14
    if low == 1: low = 14
    if high < low: high, low = low, high

    is_pair = (r1 == r2)
    is_suited = (s1 == s2)
    gap = high - low
    is_connected = (gap == 1) or (high == 14 and low == 2)  # A2 也算连张

    # 超强牌 (等级1) - 几乎永远不应该弃牌
    if is_pair and high >= 12:  # QQ, KK, AA
        return (1, "超强对子", "必须加注！考虑3-bet或4-bet")
    if high == 14 and low == 13 and is_suited:  # AKs
        return (1, "超强同花AK", "必须加注！考虑3-bet")

    # 强牌 (等级2)
    if is_pair and high >= 10:  # TT, JJ
        return (2, "大对子", "应该加注，面对3-bet可以跟注")
    if high == 14 and low == 13:  # AKo
        return (2, "AK高张", "应该加注，可以跟注3-bet")
    if high == 14 and low >= 12 and is_suited:  # AQs, AJs
        return (2, "同花A高张", "应该加注或跟注")

    # 中等牌 (等级3)
    if is_pair and high >= 7:  # 77-99
        return (3, "中等对子", "可以加注或跟注，有隐含赔率")
    if high == 14 and low >= 10:  # AT+
        return (3, "A高张", "可以加注或跟注")
    if high == 13 and low >= 11 and is_suited:  # KQs, KJs
        return (3, "同花K高张", "可以加注或跟注")
    if is_suited and is_connected and high >= 10:  # JTs, QJs
        return (3, "高同花连张", "可以加注或跟注，有坚果潜力")

    # 可玩牌 (等级4)
    if is_pair:  # 22-66
        return (4, "小对子", "后位可以跟注，追求暗三条")
    if high == 14 and is_suited:  # Axs
        return (4, "同花A小牌", "后位可以跟注，追求坚果同花")
    if is_suited and is_connected and high >= 6:  # 65s-T9s
        return (4, "同花连张", "后位可以跟注，有多种成牌可能")
    if high == 13 and low >= 10:  # KQ, KJ, KT
        return (4, "K高张", "后位可以加注或跟注")

    # 投机牌 (等级5) - 后位便宜可以玩
    if is_suited and gap <= 3 and high >= 5:  # 同花隔张
        return (5, "同花隔张", "后位便宜时可以跟注")
    if is_connected and high >= 5:  # 连张
        return (5, "杂色连张", "后位便宜时可以跟注")
    if high == 14:  # Ax
        return (5, "A弱踢脚", "后位便宜时可以跟注")

    # 弱牌 (等级6)
    return (6, "弱牌", "一般应该弃牌，除非是大盲位免费看牌")


def get_action_recommendation(equity: float, pot_odds: dict, position: str, phase: str,
                               call_amount: float, pot: float, stack: float, bb: float,
                               hole_cards=None) -> str:
    """根据当前情况生成具体行动建议"""
    recommendations = []

    # 翻牌前使用起手牌评估
    if phase == "pre_flop" and hole_cards:
        hand_rank, hand_desc, hand_advice = evaluate_preflop_hand(hole_cards)
        recommendations.append(f"【起手牌: {hand_desc}】{hand_advice}")

        # 根据起手牌等级和位置给出具体建议
        if hand_rank <= 2:  # 超强和强牌
            recommendations.append("→ 这手牌很强！应该加注建立底池，不要只是跟注")
            if call_amount > 0:
                recommendations.append("→ 面对加注可以再加注(3-bet)，展示牌力")
        elif hand_rank == 3:  # 中等牌
            if position in ["BTN", "CO", "HJ"]:
                recommendations.append("→ 后位中等牌，可以加注偷盲或隔离弱手")
            else:
                recommendations.append("→ 前位中等牌，可以跟注看翻牌")
        elif hand_rank == 4:  # 可玩牌
            if position in ["BTN", "CO"]:
                recommendations.append("→ 后位可玩牌，便宜时跟注看翻牌，有隐含赔率")
            elif position == "BB" and call_amount <= bb:
                recommendations.append("→ 大盲位加注不大，可以跟注看翻牌")
            else:
                recommendations.append("→ 前位/中位可玩牌，加注较大时可以弃牌")
        elif hand_rank == 5:  # 投机牌
            if position in ["BTN", "CO"] and call_amount <= bb * 2:
                recommendations.append("→ 后位投机牌且加注小，可以便宜跟注")
            elif position == "BB" and call_amount == 0:
                recommendations.append("→ 大盲位免费看牌，必须看！")
            else:
                recommendations.append("→ 投机牌不适合这个情况，建议弃牌")
        else:  # 弱牌
            if position == "BB" and call_amount == 0:
                recommendations.append("→ 大盲位免费看牌，任何两张都要看")
            elif position == "BB" and call_amount <= bb * 0.5:
                recommendations.append("→ 大盲位加注很小，可以便宜跟注")
            else:
                recommendations.append("→ 弱牌建议弃牌，除非你想诈唬")
    else:
        # 翻牌后使用胜率评估
        if equity >= 0.70:
            recommendations.append("【超强牌】胜率极高，应该加注/再加注榨取价值")
        elif equity >= 0.55:
            recommendations.append("【强牌】胜率领先，主动下注/加注获取价值")
        elif equity >= 0.40:
            recommendations.append("【中等牌力】可根据位置和对手决定是否下注或跟注")
        elif equity >= 0.25:
            recommendations.append("【边缘牌】如果底池赔率合适可跟注")
        else:
            recommendations.append("【弱牌】考虑弃牌，除非有好的诈唬机会")

    # 基于底池赔率的建议 (翻牌后更重要)
    if call_amount > 0 and phase != "pre_flop":
        break_even = pot_odds.get('break_even_equity', 0)
        if equity > break_even + 0.1:
            recommendations.append(f"✓ 胜率({equity:.0%})远超保本线({break_even:.0%})，跟注有利")
        elif equity > break_even:
            recommendations.append(f"✓ 胜率({equity:.0%})略高于保本线({break_even:.0%})，可以跟注")
        else:
            recommendations.append(f"✗ 胜率({equity:.0%})低于保本线({break_even:.0%})，跟注亏损")

    # 基于位置的建议
    if position in ["BTN", "CO"]:
        recommendations.append("★ 后位优势：可以更激进，信息优势明显")
    elif position == "BB":
        recommendations.append("★ 大盲位：已投入盲注，便宜时多看翻牌")

    # 下注尺度建议
    if pot > 0 and phase != "pre_flop":
        small_bet = int(pot * 0.33)
        medium_bet = int(pot * 0.66)
        large_bet = int(pot * 1.0)
        recommendations.append(f"下注参考：小${small_bet} | 中${medium_bet} | 大${large_bet}")
    elif phase == "pre_flop" and call_amount == 0:
        open_raise = int(bb * 2.5)
        recommendations.append(f"开池加注参考：${open_raise} (2.5倍大盲)")

    return "\n".join(recommendations)


def get_opponent_exploit_advice(opponents_info: list) -> str:
    """根据对手特点生成剥削建议"""
    advice = []
    for opp in opponents_info:
        name = opp.get('name', 'Unknown')
        vpip = opp.get('vpip', 0.5)
        style = opp.get('style', '未知')

        if vpip > 0.4:
            advice.append(f"  [{name}] 松玩家(VPIP高)→ 用强牌价值下注，少诈唬他")
        elif vpip < 0.2:
            advice.append(f"  [{name}] 紧玩家(VPIP低)→ 多偷他的盲注，他加注时要小心")

        if style == "激进":
            advice.append(f"  [{name}] 激进型→ 让他先下注再加注(check-raise)，用强牌陷阱他")
        elif style == "保守":
            advice.append(f"  [{name}] 保守型→ 多下注施压，他经常会弃牌")

    return "\n".join(advice) if advice else "  暂无可利用的对手弱点"


class PromptBuilder:
    """动态构建 LLM Agent 决策 Prompt"""

    @staticmethod
    def build(agent_config: dict, player: Player, game: GameEngine, memory: AgentMemory) -> str:
        state = game.get_state_snapshot()
        my_cards_str = " ".join(c.to_string() for c in player.hole_cards)

        # 计算股似率
        num_opponents = len(game.non_folded_players()) - 1
        equity = MonteCarloEquityCalculator.calculate_equity(
            player.hole_cards,
            game.community_cards,
            num_opponents,
            simulations=MC_SIMULATIONS
        )

        call_amount = max(0.0, game.street_bet - player.current_bet)
        pot_odds = calculate_pot_odds(game.pot, call_amount)
        ev = calculate_ev(equity, game.pot, call_amount)

        # 对手分析摘要
        opponent_lines = []
        for p in game.players:
            if p.id == player.id or p.status.value == "folded":
                continue
            profile = memory.get_opponent_profile(p.id)
            style = "激进" if profile.aggression > 0.5 else "保守"
            recent = " → ".join(a["action"] for a in profile.recent_actions[-3:]) or "无记录"
            opponent_lines.append(
                f"  [{p.name}] 筹码 ${p.stack:.0f} | 风格: {style}"
                f" | VPIP: {profile.vpip:.0%} | 近期: {recent}"
            )
        opponent_section = "\n".join(opponent_lines) if opponent_lines else "  无对手信息"

        # 可用行动列表
        valid_actions = game.get_valid_actions(player)
        actions_str = " | ".join(a.value for a in valid_actions)

        # 最近对话
        recent_speech = game.get_recent_speech(max_lines=5)
        speech_display = recent_speech if recent_speech else "  暂无对话"

        # 根据筹码量给出策略建议（大盲注=20）
        bb = game.big_blind
        stack_bb = player.stack / bb if bb > 0 else 50
        if stack_bb < 15:
            stack_advice = "短码(<15BB)：推All-in或弃牌，不宜平跟"
        elif stack_bb < 30:
            stack_advice = "较短筹码(15-30BB)：可加注All-in施压，谨慎跟注"
        elif stack_bb < 50:
            stack_advice = "中等筹码(30-50BB)：标准打法，正常加注"
        elif stack_bb < 80:
            stack_advice = "较深筹码(50-80BB)：可玩更多手牌，适当诈唬"
        else:
            stack_advice = "深码(>80BB)：手牌范围宽，可用筹码施压对手"

        # 位置信息
        all_positions = ", ".join(
            f"{p.name}({p.position})" for p in game.players
            if p.status.value != "folded"
        )

        # 生成行动建议
        action_recommendation = get_action_recommendation(
            equity, pot_odds, player.position, state['phase'],
            call_amount, game.pot, player.stack, bb,
            hole_cards=player.hole_cards
        )

        # 生成对手剥削建议
        opponents_info = []
        for p in game.players:
            if p.id == player.id or p.status.value == "folded":
                continue
            profile = memory.get_opponent_profile(p.id)
            opponents_info.append({
                'name': p.name,
                'vpip': profile.vpip,
                'style': "激进" if profile.aggression > 0.5 else "保守"
            })
        exploit_advice = get_opponent_exploit_advice(opponents_info)

        prompt = f"""你是德州扑克玩家【{agent_config['name']}】。

【性格设定】
{agent_config['persona']}
风险偏好: {agent_config['risk_profile']}

【当前牌局状态】
- 你的位置: {player.position}
- 全场位置一览: {all_positions}
- 总人数: {len(game.non_folded_players())} (未弃牌)
- 你的手牌: {my_cards_str}
- 你的筹码: ${player.stack:.0f}
- 底池大小: ${state['pot']:.0f}
- 下注轮: {state['phase']}
- 公共牌: {', '.join(c.to_string() for c in game.community_cards) if game.community_cards else '未发'}
- 当前最高下注: ${state['street_bet']:.0f}
- 你需要跟注: ${call_amount:.0f}

【位置说明】
- BTN(庄家): 翻牌后最后行动，最具优势
- CO(关煞位): 庄家右侧，翻牌前仅次于庄家
- HJ/MP(中间位): 中间位置
- UTG(枪口位): 翻牌前最先行动，最不利位置
- SB(小盲): 翻牌前第二行动，已投入小盲注
- BB(大盲): 翻牌前最后行动，已投入大盲注

【策略要点】
- 筹码量: ${player.stack:.0f} — {stack_advice}
- 位置越靠后，可玩的手牌范围越宽

【数学分析】
- 你的股似率(胜率): {equity:.1%}
- 底池赔率: {pot_odds['pot_odds']:.1%}
- 保本所需最低胜率: {pot_odds['break_even_equity']:.1%}
- 期望值评估: {"正期望值 ✓ (值得跟注)" if ev > 0 else "负期望值 ✗ (不建议跟注)"}

【⚡ 行动建议 - 请认真参考！】
{action_recommendation}

【对手分析】
{opponent_section}

【🎯 对手弱点利用】
{exploit_advice}

【桌上对话】
{speech_display}

【你的历史记录】
{memory.get_prompt_summary()}

【可用行动】
{actions_str}

请严格按照以下格式回复，三个部分都必须完整输出:

<thinking>
(结合【行动建议】和数学分析，考虑位置、对手弱点，做出最优决策。50-100字)
</thinking>

<action>
fold | check | call | raise {{金额}} | allin
(注意：有强牌时要主动加注获取价值！不要只是跟注！)
</action>

<speech>
(每一轮都说1句话！保持角色一致，可以虚张声势、放狠话、误导对手或表达情绪。你的话会直接影响对手的判断！
【重要】绝对不能在发言中透露你的具体手牌！不能说"我有AA"、"我拿了同花"等。可以暗示强弱但不能明说！)
</speech>"""

        return prompt
