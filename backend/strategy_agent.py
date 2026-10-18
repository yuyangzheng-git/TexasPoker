"""
风格化混合策略 AI（本地算法模式，不调用 LLM）

设计目标是给真人一个"像人、风格各异、难度可调、不作弊"的练习对手：

1. 公平：只用自己的底牌 + 公开行动 + 公开统计（PublicStatsTracker）。
2. 风格：人格配置里的 vpip_target / pfr_target / risk_profile 直接决定入池宽度、
   加注倾向、诈唬频率、跟注黏性和慢打倾向。
3. 混合策略：每个决策先算出 {弃牌, 跟注/过牌, 加注} 的概率，再按概率抽样，
   同样的局面不会总是同一个动作，避免用户"读 bot"。
4. 牌力：翻后用对手范围加权的胜率（range_equity），而不是对随机手牌的胜率。
5. 难度：difficulty_level 控制技能 skill —— 低难度会忽略部分范围信息、胜率估计带噪声、
   不做针对性剥削；高难度反之。
6. 可解释：thinking 字段给出范围、胜率、底池赔率、各动作概率，供本手结束后复盘展示。

接口与 LLMAgent 一致：async decide(game, timeout, on_chunk) -> ParsedResponse。
"""
import asyncio
import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from agent_engine import ParsedResponse
from fast_eval import MADE_CATEGORY_NAMES, codes, made_category
from game_engine import Action, ActionType, GameEngine, GamePhase, Player, PlayerStatus
from preflop_ranges import class_name, hand_features, percentile_of_cards
from range_equity import RangeSpec, infer_range, range_equity

# 各位置开池宽度相对 VPIP 目标的倍数（6 人桌标定，见 docs/algorithm-upgrade.md）
POSITION_OPEN_MULT = {
    "UTG": 0.55, "EP": 0.6, "MP": 0.68, "LJ": 0.72, "HJ": 0.8, "CO": 1.0,
    "BTN": 1.45, "SB": 1.0, "BB": 0.6, "BTN/SB": 1.6, "": 0.8,
}
LATE_POSITIONS = {"CO", "BTN", "BTN/SB"}

DIFFICULTY_SKILL = {"easy": 0.35, "medium": 0.65, "hard": 0.9}


@dataclass
class StyleProfile:
    vpip: float = 0.27          # 目标入池率
    pfr: float = 0.19           # 目标翻前加注率
    aggression: float = 0.55    # 翻后主动下注/加注倾向 0~1
    bluff: float = 0.22         # 诈唬倾向 0~1
    stickiness: float = 0.0     # 跟注黏性：>0 更爱跟注（降低所需胜率）
    trap: float = 0.1           # 慢打倾向
    skill: float = 0.65         # 技能（难度）
    exploit: float = 0.5        # 针对对手漏洞调整的力度
    temperature: float = 0.6    # 混合程度（越高越随机）
    label: str = "常规"

    @classmethod
    def from_persona(cls, persona: dict) -> "StyleProfile":
        def mid(v, default):
            if isinstance(v, (list, tuple)) and v:
                return sum(v) / len(v)
            if isinstance(v, (int, float)):
                return float(v)
            return default

        prof = cls(
            vpip=mid(persona.get("vpip_target"), 0.27),
            pfr=mid(persona.get("pfr_target"), 0.19),
            temperature=float(persona.get("temperature", 0.6)),
            skill=DIFFICULTY_SKILL.get(persona.get("difficulty_level", "medium"), 0.65),
        )
        risk = (persona.get("risk_profile") or "").lower()
        style = persona.get("style") or ""
        label = []
        if "hyper" in risk:
            prof.aggression, prof.bluff, prof.stickiness = 0.9, 0.5, 0.03
            label.append("超激进")
        elif "aggressive" in risk:
            prof.aggression, prof.bluff = 0.75, 0.32
            label.append("激进")
        if "tight" in risk:
            prof.bluff = min(prof.bluff, 0.16)
            prof.stickiness -= 0.02
            label.append("紧")
        if "passive" in risk:
            prof.aggression, prof.bluff, prof.stickiness = 0.28, 0.06, prof.stickiness + 0.08
            label.append("被动")
        if "loose" in risk:
            prof.stickiness += 0.05
            label.append("松")
        if "deceptive" in risk or "soul" in risk:
            prof.trap, prof.bluff = 0.3, max(prof.bluff, 0.3)
            label.append("诡诈")
        if "exploitative" in risk or "elite" in risk or "smart" in risk:
            prof.exploit = 1.0
            label.append("剥削型")
        if "gto" in risk or "balanced" in risk or "analytical" in risk:
            prof.temperature = max(prof.temperature, 0.55)
            label.append("均衡")
        if "recreational" in risk or "learning" in risk:
            prof.stickiness += 0.04
            prof.skill = min(prof.skill, 0.4)
        prof.label = "/".join(label) or style or "常规"
        return prof


def _sigmoid(x: float) -> float:
    if x < -30:
        return 0.0
    if x > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _round_chips(amount: float, unit: float) -> float:
    unit = max(1.0, unit)
    return max(unit, round(amount / unit) * unit)


class StrategyAgent:
    """本地算法 AI。agent_config 为 agent_personas.json 中的一项。"""

    kind = "strategy"

    def __init__(self, agent_config: dict, player: Player, seed: Optional[int] = None,
                 simulations: Optional[int] = None):
        self.config = agent_config
        self.player = player
        self.style = StyleProfile.from_persona(agent_config)
        self.rng = random.Random(seed)
        self.tracker = None
        # 在线自校准：根据自己的实测 VPIP/PFR 缩放入池/加注宽度，使统计贴近人格目标
        self.vpip_scale = 1.0
        self.pfr_scale = 1.0
        self._calib_hands = 0
        base_sims = 700 if simulations is None else simulations
        # 低技能用更少的模拟次数（更快，也更"粗糙"）
        self.simulations = max(150, int(base_sims * (0.5 + 0.5 * self.style.skill)))

    # ── 与 LLMAgent 保持一致的辅助接口 ─────────────────────────────
    def attach_tracker(self, tracker):
        self.tracker = tracker

    def update_memory(self, won: bool, amount: float):  # 兼容旧调用
        return None

    def observe_opponent(self, opponent_id: str, action_type: str, context: dict):
        return None

    # ── 决策入口 ───────────────────────────────────────────────────
    async def decide(self, game: GameEngine, timeout: float = 20.0,
                     on_chunk: Optional[Callable] = None) -> ParsedResponse:
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.decide_sync, game), timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — 任何异常都退回到安全动作
            to_call = max(0.0, game.street_bet - self.player.current_bet)
            kind = ActionType.CHECK if to_call <= 0 else ActionType.FOLD
            return ParsedResponse(thinking=f"（本地策略异常，安全动作：{exc!s:.40}）",
                                  action=Action(self.player.id, kind), speech="",
                                  fallback_reason=f"strategy_error:{exc!s:.60}")

    def _calibrate(self):
        if self.tracker is None:
            return
        st = self.tracker.get(self.player.id)
        if st.hands < 20 or st.hands == self._calib_hands:
            return
        self._calib_hands = st.hands
        obs_v = st.vpip_hands / st.hands
        obs_p = st.pfr_hands / st.hands
        # 乘法式小步调整，限制在合理区间内
        self.vpip_scale *= ((self.style.vpip + 0.01) / (obs_v + 0.01)) ** 0.08
        self.pfr_scale *= ((self.style.pfr + 0.01) / (obs_p + 0.01)) ** 0.08
        self.vpip_scale = min(2.5, max(0.5, self.vpip_scale))
        self.pfr_scale = min(2.5, max(0.5, self.pfr_scale))

    def decide_sync(self, game: GameEngine) -> ParsedResponse:
        player = self.player
        if game.phase == GamePhase.PRE_FLOP:
            self._calibrate()
        valid = game.get_valid_actions(player)
        if not valid:
            return ParsedResponse(thinking="无可用行动", action=Action(player.id, ActionType.CHECK))
        if game.phase == GamePhase.PRE_FLOP:
            probs, sizes, notes = self._preflop(game, valid)
        else:
            probs, sizes, notes = self._postflop(game, valid)
        choice = self._sample(probs)
        action = self._to_action(game, valid, choice, sizes)
        prob_text = " / ".join(f"{self._cn(k)} {v:.0%}" for k, v in probs.items() if v >= 0.005)
        notes.append(f"混合策略：{prob_text} → 选择 {self._describe(action, game)}")
        return ParsedResponse(thinking="\n".join(notes), action=action,
                              speech=self._speech(choice, game))

    # ── 翻牌前 ─────────────────────────────────────────────────────
    def _preflop(self, game: GameEngine, valid: List[ActionType]):
        st = self.style
        player = self.player
        bb = game.big_blind
        pos = player.position or ""
        hole = player.hole_cards
        p = percentile_of_cards(hole)
        feats = hand_features(*codes(hole))
        name = class_name(hole[0].rank, hole[0].suit, hole[1].rank, hole[1].suit)

        # 隐含赔率修正：小对子、同花连张在多人底池里比"对随机手牌胜率"更值钱
        eff = p
        if feats["pair"] and feats["high"] <= 7:
            eff -= 0.12
        elif feats["suited"] and feats["connected"] and feats["high"] >= 6:
            eff -= 0.06
        elif feats["suited"] and feats["high"] == 14:
            eff -= 0.04
        eff = max(0.0, eff)

        raises, limpers, last_raise_to, raiser_ids = self._preflop_context(game)
        to_call = max(0.0, game.street_bet - player.current_bet)
        stack_bb = (player.stack + player.current_bet) / bb
        pos_mult = POSITION_OPEN_MULT.get(pos, 0.8)
        temp = 0.025 + 0.03 * st.temperature
        notes = [f"【翻牌前】手牌 {name}（强度约前 {p:.0%}），位置 {pos or '?'}，筹码 {stack_bb:.0f}BB，风格 {st.label}"]

        probs = {"fold": 0.0, "call": 0.0, "raise": 0.0}
        sizes: Dict[str, float] = {}

        # 短码：推或弃
        if stack_bb <= 12:
            push_width = min(0.6, (st.vpip * 1.1) * (14.0 / max(stack_bb, 3)) ** 0.5 * pos_mult)
            if raises:
                push_width *= 0.45
            pr = _sigmoid((push_width - eff) / temp)
            probs["raise"] = pr
            probs["call" if to_call == 0 else "fold"] = 1 - pr
            sizes["raise"] = float("inf")
            notes.append(f"短码推弃：全下宽度约前 {push_width:.0%}")
            return self._normalize(probs, valid, to_call), sizes, notes

        vs, ps = self.vpip_scale, self.pfr_scale
        if raises == 0:
            open_w = st.pfr * pos_mult * 1.2 * ps
            call_w = st.vpip * pos_mult * 1.15 * vs
            if pos == "BB":
                # 大盲面对平跟：过牌为主，强牌加注隔离
                pr = _sigmoid((st.pfr * 0.5 - eff) / temp)
                probs["raise"], probs["call"] = pr, 1 - pr
                sizes["raise"] = bb * (3.5 + limpers)
                notes.append("大盲位无人加注，免费看牌为主")
            else:
                pr = _sigmoid((open_w - eff) / temp)
                # 被动风格会平跟一部分手牌；其他风格"要么加注要么弃牌"
                limp_tend = min(1.0, max(0.0, 0.65 - st.aggression) * 2.0)
                pc = max(0.0, _sigmoid((call_w - eff) / temp) - pr) * (limp_tend if limpers == 0 else 1.0)
                if pos == "SB" and limpers == 0:
                    pc = max(pc, max(0.0, _sigmoid((call_w * 1.2 - eff) / temp) - pr) * 0.5)
                probs["raise"], probs["call"] = pr, pc
                probs["fold"] = max(0.0, 1 - pr - pc)
                sizes["raise"] = bb * ((3.0 if pos == "SB" else 2.5) + limpers)
                notes.append(f"无人加注：开池宽度约前 {open_w:.0%}，入池宽度约前 {call_w:.0%}"
                             + (f"，前面 {limpers} 人平跟" if limpers else ""))
        elif raises == 1:
            raise_bb = last_raise_to / bb
            size_factor = (2.5 / max(raise_bb, 2.0)) ** 0.6
            raiser_spec = self._raiser_spec(game, raiser_ids)
            # 对手开池越宽，我们的继续范围越宽
            widen = 1.0
            if raiser_spec is not None:
                widen = min(1.8, max(0.7, (raiser_spec.top / 0.2) ** 0.5))
            three_w = st.pfr * 0.38 * ps * size_factor * widen * (1.25 if pos in LATE_POSITIONS else 1.0)
            call_w = max(0.03, st.vpip - st.pfr * 0.4) * 1.05 * vs * size_factor * widen
            if pos == "BB":
                call_w *= 1.6
            elif pos == "SB":
                call_w *= 0.7
            pr = _sigmoid((three_w - eff) / temp)
            # 少量 3bet 诈唬：同花 A 小牌 / 同花连张
            if feats["suited"] and (feats["high"] == 14 or feats["connected"]) and eff > three_w:
                pr = max(pr, st.bluff * 0.25)
            pc = max(0.0, _sigmoid((call_w - eff) / temp) - pr)
            probs["raise"], probs["call"] = pr, pc
            probs["fold"] = max(0.0, 1 - pr - pc)
            mult = 3.0 if pos in LATE_POSITIONS else 3.6
            sizes["raise"] = last_raise_to * mult + bb * limpers
            desc = raiser_spec.describe() if raiser_spec else "未知"
            notes.append(f"面对加注到 {raise_bb:.1f}BB（对手：{desc}）：3bet 宽度约前 {three_w:.1%}，跟注宽度约前 {call_w:.0%}")
        elif raises == 2:
            i_opened = player.id in raiser_ids[:1]
            four_w = 0.022 + 0.01 * st.aggression
            call_w = 0.075 if i_opened else 0.04
            pr = _sigmoid((four_w - p) / 0.008)
            pc = max(0.0, _sigmoid((call_w - p) / 0.012) - pr)
            probs["raise"], probs["call"] = pr, pc
            probs["fold"] = max(0.0, 1 - pr - pc)
            sizes["raise"] = last_raise_to * 2.3
            notes.append(f"面对 3bet：4bet 宽度约前 {four_w:.1%}，跟注宽度约前 {call_w:.1%}")
        else:
            pr = _sigmoid((0.012 - p) / 0.004)
            pc = max(0.0, _sigmoid((0.03 - p) / 0.006) - pr)
            probs["raise"], probs["call"] = pr, pc
            probs["fold"] = max(0.0, 1 - pr - pc)
            sizes["raise"] = float("inf")
            notes.append("面对 4bet 以上：只用最强的手牌继续")

        return self._normalize(probs, valid, to_call), sizes, notes

    def _preflop_context(self, game: GameEngine) -> Tuple[int, int, float, List[str]]:
        raises = 0
        limpers = 0
        level = game.big_blind
        raiser_ids: List[str] = []
        for act in game.action_history:
            if act.phase and act.phase != GamePhase.PRE_FLOP.value:
                break
            if act.type == ActionType.RAISE or (act.type == ActionType.ALLIN and act.amount > level):
                raises += 1
                level = max(level, act.amount)
                raiser_ids.append(act.player_id)
            elif act.type == ActionType.CALL and raises == 0:
                limpers += 1
        return raises, limpers, max(level, game.street_bet), raiser_ids

    def _raiser_spec(self, game: GameEngine, raiser_ids: List[str]) -> Optional[RangeSpec]:
        if not raiser_ids:
            return None
        opp = game._get_player(raiser_ids[-1])
        if opp is None:
            return None
        return infer_range(game, opp, self.tracker)

    # ── 翻牌后 ─────────────────────────────────────────────────────
    def _postflop(self, game: GameEngine, valid: List[ActionType]):
        st = self.style
        player = self.player
        opponents = [p for p in game.non_folded_players() if p.id != player.id]
        n_opp = max(1, len(opponents))
        specs = [infer_range(game, o, self.tracker) for o in opponents]
        eqr = range_equity(player.hole_cards, game.community_cards, specs,
                           simulations=self.simulations, rng=self.rng)
        # 低技能：部分忽略范围信息（更接近"按随机手牌算"）
        range_trust = 0.35 + 0.65 * st.skill
        eq = eqr["equity"] * range_trust + eqr["equity_random"] * (1 - range_trust)
        eq += self.rng.gauss(0, 0.07 * (1 - st.skill))
        eq = min(0.99, max(0.01, eq))

        hole_c = codes(player.hole_cards)
        board_c = codes(game.community_cards)
        cat = made_category(hole_c, board_c)
        street = game.phase.value
        is_river = game.phase == GamePhase.RIVER
        pot = game.pot
        to_call = max(0.0, game.street_bet - player.current_bet)
        pot_odds = to_call / (pot + to_call) if to_call > 0 else 0.0
        ip = self._in_position(game)
        was_aggressor = self._preflop_aggressor(game) == player.id

        # 剥削调整（只有中高技能才会用统计数据）
        bluff_mult, value_shift, sticky_adj, exploit_note = self._exploit_adjust(opponents)

        notes = [
            f"【{ {'flop': '翻牌', 'turn': '转牌', 'river': '河牌'}.get(street, street)}】成牌：{MADE_CATEGORY_NAMES[cat]}，"
            f"{'有' if ip else '无'}位置，{n_opp} 个对手",
            "对手范围：" + "；".join(f"{o.name}：{s.describe()}" for o, s in zip(opponents, specs)),
            f"范围加权胜率 {eqr['equity']:.0%}（若按随机手牌算 {eqr['equity_random']:.0%}），"
            f"决策采用 {eq:.0%}" + (f"，底池赔率 {pot_odds:.0%}" if to_call > 0 else ""),
        ]
        if exploit_note:
            notes.append(exploit_note)

        probs = {"fold": 0.0, "call": 0.0, "raise": 0.0}
        sizes: Dict[str, float] = {}
        spr = player.stack / max(pot, 1.0)

        if to_call <= 0:
            thr = 1.0 / (n_opp + 1) + 0.2 + value_shift
            p_value = _sigmoid((eq - thr) / 0.06) * (0.5 + 0.5 * st.aggression)
            if eq > 0.82 and not is_river:
                p_value *= 1.0 - st.trap * 0.7  # 慢打
            draw = cat == 1 and not is_river
            p_bluff = st.bluff * bluff_mult * (0.65 if draw else (0.35 if cat == 0 else 0.08))
            p_bluff *= (1.3 if ip else 0.85) / n_opp
            if was_aggressor and street == GamePhase.FLOP.value:
                p_bluff += 0.25 * st.aggression / n_opp  # 持续下注
            p_bluff = min(0.8, p_bluff)
            p_bet = min(0.97, p_value + (1 - p_value) * p_bluff * (1.0 if eq < thr else 0.3))
            probs["raise"] = p_bet
            probs["call"] = 1 - p_bet  # 过牌
            if eq >= 0.75:
                frac = self.rng.choice([0.66, 0.75, 1.0] if st.aggression > 0.6 else [0.5, 0.66, 0.75])
            elif eq >= thr:
                frac = self.rng.choice([0.33, 0.5])
            else:
                frac = self.rng.choice([0.5, 0.66])
            if is_river and (eq >= 0.8 or eq < 0.25):
                frac = max(frac, 0.75)  # 河牌极化
            sizes["raise"] = pot * frac
            notes.append(f"无人下注：价值下注阈值 {thr:.0%}，下注概率 {p_bet:.0%}，尺度约 {frac:.0%} 底池")
        else:
            margin = 0.025 - st.stickiness - sticky_adj
            eq_eff = eq + (0.07 if (cat == 1 and not is_river and spr > 1.5) else 0.0)
            p_cont = _sigmoid((eq_eff - pot_odds - margin) / 0.04)
            raise_thr = 0.7 + 0.05 * (n_opp - 1) + value_shift
            p_raise = _sigmoid((eq - raise_thr) / 0.05) * (0.35 + 0.65 * st.aggression) * (1 - st.trap * 0.5)
            if cat == 1 and not is_river:
                p_raise = max(p_raise, st.bluff * bluff_mult * 0.3 * (1.0 if to_call < pot * 0.6 else 0.4))
            p_raise = min(p_raise, 0.9)
            probs["raise"] = p_raise
            probs["call"] = (1 - p_raise) * p_cont
            probs["fold"] = (1 - p_raise) * (1 - p_cont)
            sizes["raise"] = game.street_bet * 3.0 + (pot - game.street_bet) * 0.3
            notes.append(f"面对下注 {to_call:.0f}：继续所需胜率约 {pot_odds + margin:.0%}，"
                         f"加注阈值 {raise_thr:.0%}")
        return self._normalize(probs, valid, to_call), sizes, notes

    def _exploit_adjust(self, opponents: List[Player]):
        st = self.style
        if self.tracker is None or st.skill < 0.6 or not opponents:
            return 1.0, 0.0, 0.0, ""
        weight = st.exploit * min(1.0, (st.skill - 0.5) * 2)
        stats = [self.tracker.get(o.id) for o in opponents]
        reliable = [s for s in stats if s.hands >= 12]
        if not reliable:
            return 1.0, 0.0, 0.0, ""
        ftb = sum(s.fold_to_bet for s in reliable) / len(reliable)
        af = sum(s.af for s in reliable) / len(reliable)
        bluff_mult = 1.0 + weight * (ftb - 0.45) * 2.5       # 爱弃牌 → 多诈唬
        value_shift = -weight * max(0.0, 0.4 - ftb) * 0.25    # 跟注站 → 薄价值
        sticky_adj = weight * max(0.0, af - 2.5) * 0.02       # 对手很凶 → 多抓诈唬
        bluff_mult = min(1.8, max(0.3, bluff_mult))
        labels = "、".join(f"{o.name}({self.tracker.get(o.id).style_label()})" for o in opponents
                          if self.tracker.get(o.id).hands >= 12)
        note = (f"针对性调整：{labels}；面对下注弃牌率 {ftb:.0%}，激进度 {af:.1f}"
                f" → 诈唬×{bluff_mult:.2f}")
        return bluff_mult, value_shift, sticky_adj, note

    def _in_position(self, game: GameEngine) -> bool:
        n = len(game.players)
        alive = [p for p in game.non_folded_players()]
        def offset(p):
            return (game.players.index(p) - game.dealer_idx - 1) % n
        return offset(self.player) == max(offset(p) for p in alive)

    def _preflop_aggressor(self, game: GameEngine) -> Optional[str]:
        last = None
        level = game.big_blind
        for act in game.action_history:
            if act.phase and act.phase != GamePhase.PRE_FLOP.value:
                break
            if act.type == ActionType.RAISE or (act.type == ActionType.ALLIN and act.amount > level):
                last = act.player_id
                level = max(level, act.amount)
        return last

    # ── 通用工具 ───────────────────────────────────────────────────
    def _normalize(self, probs: Dict[str, float], valid: List[ActionType], to_call: float) -> Dict[str, float]:
        if to_call <= 0:
            # 无需跟注时弃牌没有意义，合并到过牌
            probs["call"] = probs.get("call", 0.0) + probs.get("fold", 0.0)
            probs["fold"] = 0.0
        can_raise = ActionType.RAISE in valid or ActionType.ALLIN in valid
        if not can_raise:
            probs["call"] += probs.get("raise", 0.0)
            probs["raise"] = 0.0
        total = sum(probs.values())
        if total <= 0:
            return {"call": 1.0} if to_call <= 0 else {"fold": 1.0}
        return {k: v / total for k, v in probs.items()}

    def _sample(self, probs: Dict[str, float]) -> str:
        x = self.rng.random()
        acc = 0.0
        for k, v in probs.items():
            acc += v
            if x < acc:
                return k
        return max(probs, key=probs.get)

    def _to_action(self, game: GameEngine, valid: List[ActionType], choice: str,
                   sizes: Dict[str, float]) -> Action:
        player = self.player
        to_call = max(0.0, game.street_bet - player.current_bet)
        if choice == "fold":
            if to_call <= 0 and ActionType.CHECK in valid:
                return Action(player.id, ActionType.CHECK)
            return Action(player.id, ActionType.FOLD)
        if choice == "call":
            if ActionType.CHECK in valid:
                return Action(player.id, ActionType.CHECK)
            if ActionType.CALL in valid:
                return Action(player.id, ActionType.CALL, amount=to_call)
            return Action(player.id, ActionType.ALLIN, amount=player.stack)
        # raise
        max_to = player.stack + player.current_bet
        target = sizes.get("raise", game.minimum_raise_to())
        if game.phase != GamePhase.PRE_FLOP and target != float("inf"):
            target = game.street_bet + target if to_call <= 0 else target
        unit = game.min_bet  # 小盲注，下注额取整到小盲的倍数
        if target != float("inf"):
            target = _round_chips(target, unit)
            target = max(target, game.minimum_raise_to())
        # 下注超过剩余筹码的 85% 时直接全下（避免留下尴尬的小筹码）
        if target == float("inf") or target >= max_to * 0.85 or ActionType.RAISE not in valid:
            if ActionType.ALLIN in valid:
                return Action(player.id, ActionType.ALLIN, amount=player.stack)
            if ActionType.CALL in valid:
                return Action(player.id, ActionType.CALL, amount=to_call)
            return Action(player.id, ActionType.CHECK)
        return Action(player.id, ActionType.RAISE, amount=float(min(target, max_to)))

    @staticmethod
    def _cn(key: str) -> str:
        return {"fold": "弃牌", "call": "跟注/过牌", "raise": "加注/下注"}[key]

    @staticmethod
    def _describe(action: Action, game: GameEngine) -> str:
        if action.type == ActionType.RAISE:
            return f"{'下注' if game.street_bet == 0 else '加注'}到 {action.amount:.0f}"
        return {"fold": "弃牌", "check": "过牌", "call": "跟注", "allin": "全下"}[action.type.value]

    _LINES = {
        "aggressive": ["来点刺激的。", "这池子我要了。", "跟不跟，看你胆量。", "别犹豫，加注才是王道。"],
        "calm": ["嗯。", "慢慢来。", "看看再说。", "稳一点。"],
        "fun": ["哈哈，玩玩嘛！", "运气来了挡不住～", "这牌有点意思。", "冲就完了！"],
    }

    def _speech(self, choice: str, game: GameEngine) -> str:
        # 偶尔说一句话，只表达情绪，不透露任何牌面信息
        if self.rng.random() > 0.12:
            return ""
        st = self.style
        if st.aggression >= 0.7:
            pool = self._LINES["aggressive"]
        elif "松" in st.label or st.stickiness > 0.05:
            pool = self._LINES["fun"]
        else:
            pool = self._LINES["calm"]
        return self.rng.choice(pool)
