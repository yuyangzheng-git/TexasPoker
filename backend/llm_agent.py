"""
LLM Agent - Claude Haiku 版本
使用 claude-haiku-4-5-20251001 模型
"""
import re
import asyncio
import os
import json
from typing import Optional, Callable
from openai import AsyncOpenAI

from game_engine import GameEngine, Player, Action, ActionType, GamePhase
from monte_carlo_equity import MonteCarloEquityCalculator
from agent_engine import (
    AgentMemory, ParsedResponse, PromptBuilder, calculate_pot_odds, evaluate_preflop_hand
)

# 加载全局配置
with open("../config/game_config.json") as _f:
    _game_cfg = json.load(_f)
MC_SIMULATIONS = _game_cfg.get("monte_carlo", {}).get("simulations", 5000)

# ─── Claude API 配置 ─────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://cn.api.openai-next.com/")

# 使用 Claude Haiku 模型
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def get_model_for_phase(phase: GamePhase) -> str:
    """返回 Claude 模型"""
    return DEFAULT_MODEL


# ─── 响应解析器 ───────────────────────────────────────────────────

class ResponseParser:
    """解析 DeepSeek 返回的结构化响应"""

    @staticmethod
    def parse(raw: str, player: Player, game: GameEngine) -> ParsedResponse:
        thinking   = ResponseParser._extract_tag(raw, "thinking")
        action_str = ResponseParser._extract_tag(raw, "action")
        speech     = ResponseParser._extract_tag(raw, "speech")
        action = ResponseParser._parse_action(action_str, player, game)
        action = ResponseParser._validate_action(action, player, game)
        return ParsedResponse(thinking=thinking or "", action=action, speech=speech or "")

    @staticmethod
    def _extract_tag(text: str, tag: str) -> Optional[str]:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _parse_action(s: Optional[str], player: Player, game: GameEngine) -> Action:
        if not s:
            return ResponseParser._fallback_action(player, game)
        s = s.strip().lower()

        if s.startswith("fold"):
            return Action(player_id=player.id, type=ActionType.FOLD)
        if s.startswith("check"):
            return Action(player_id=player.id, type=ActionType.CHECK)
        if s.startswith("call"):
            amt = game.street_bet - player.current_bet
            return Action(player_id=player.id, type=ActionType.CALL, amount=amt)
        if s.startswith("allin"):
            return Action(player_id=player.id, type=ActionType.ALLIN, amount=player.stack)

        m = re.search(r"raise\s+(\d+(?:\.\d+)?)", s)
        if m:
            return Action(player_id=player.id, type=ActionType.RAISE, amount=float(m.group(1)))

        return ResponseParser._fallback_action(player, game)

    @staticmethod
    def _validate_action(action: Action, player: Player, game: GameEngine) -> Action:
        if action.type == ActionType.CHECK and player.current_bet != game.street_bet:
            amt = game.street_bet - player.current_bet
            return Action(player_id=player.id, type=ActionType.CALL, amount=amt)
        if action.type == ActionType.CALL and game.street_bet == player.current_bet:
            return Action(player_id=player.id, type=ActionType.CHECK)
        if action.type == ActionType.RAISE:
            min_r = max(game.street_bet * 2, game.big_blind)
            max_r = player.stack + player.current_bet
            if action.amount < min_r:
                action.amount = min_r
            if action.amount > max_r:
                return Action(player_id=player.id, type=ActionType.ALLIN, amount=player.stack)
        return action

    @staticmethod
    def _fallback_action(player: Player, game: GameEngine) -> Action:
        call_amount = game.street_bet - player.current_bet
        if call_amount <= 0:
            return Action(player_id=player.id, type=ActionType.CHECK)

        # 翻牌前使用起手牌评估
        if game.phase == GamePhase.PRE_FLOP:
            hand_rank, _, _ = evaluate_preflop_hand(player.hole_cards)
            # 超强和强牌: 必跟
            if hand_rank <= 2:
                return Action(player_id=player.id, type=ActionType.CALL, amount=call_amount)
            # 中等牌: 跟注不大就跟
            if hand_rank == 3 and call_amount <= game.big_blind * 4:
                return Action(player_id=player.id, type=ActionType.CALL, amount=call_amount)
            # 可玩牌: 后位且便宜就跟
            if hand_rank == 4 and player.position in ["BTN", "CO", "BB"] and call_amount <= game.big_blind * 3:
                return Action(player_id=player.id, type=ActionType.CALL, amount=call_amount)
            # 大盲位特殊处理
            if player.position == "BB" and call_amount <= game.big_blind * 2:
                return Action(player_id=player.id, type=ActionType.CALL, amount=call_amount)

        # 翻牌后使用胜率评估
        equity = MonteCarloEquityCalculator.calculate_equity(
            player.hole_cards, game.community_cards,
            max(len(game.non_folded_players()) - 1, 1), simulations=MC_SIMULATIONS
        )
        pot_odds = calculate_pot_odds(game.pot, call_amount)
        if equity > pot_odds["break_even_equity"]:
            return Action(player_id=player.id, type=ActionType.CALL, amount=call_amount)
        return Action(player_id=player.id, type=ActionType.FOLD)


# ─── LLM Agent 主类 ────────────────────────────────────────────────

class LLMAgent:
    """
    独立的 LLM Agent 玩家
    使用 Claude Haiku 模型进行决策
    """

    def __init__(self, agent_config: dict, player: Player):
        self.config      = agent_config
        self.player      = player
        self.memory      = AgentMemory()
        self.temperature = float(agent_config.get("temperature", 0.7))

        # OpenAI 兼容客户端 → Claude API
        self.client = AsyncOpenAI(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
        )

    def _select_model(self, phase: GamePhase) -> str:
        """返回 Claude 模型"""
        model = get_model_for_phase(phase)
        return model

    async def decide(
        self,
        game: GameEngine,
        timeout: float = 20.0,
        on_chunk: Optional[Callable] = None
    ) -> ParsedResponse:
        """
        异步决策入口
        1. 选择模型
        2. 构建 Prompt
        3. 调用 Claude API（支持流式）
        4. 解析响应 + 规则校验
        """
        model = self._select_model(game.phase)
        prompt = PromptBuilder.build(self.config, self.player, game, self.memory)

        print(f"[{self.config['name']}] phase={game.phase.value}  model={model}")

        try:
            raw = await asyncio.wait_for(
                self._call_api(prompt, model, on_chunk),
                timeout=timeout
            )
            return ResponseParser.parse(raw, self.player, game)

        except asyncio.TimeoutError:
            fallback = ResponseParser._fallback_action(self.player, game)
            return ParsedResponse(
                thinking=f"（{model} 超时，自动决策）",
                action=fallback, speech=""
            )
        except Exception as e:
            print(f"[LLMAgent:{self.config['name']}] API error: {e}")
            fallback = ResponseParser._fallback_action(self.player, game)
            return ParsedResponse(
                thinking=f"（API 错误，自动决策: {str(e)[:40]}）",
                action=fallback, speech=""
            )

    async def _call_api(
        self,
        prompt: str,
        model: str,
        on_chunk: Optional[Callable] = None
    ) -> str:
        """
        调用 Claude OpenAI 兼容 API
        system: 固定人格 + 德州扑克规则  |  user: 动态牌局状态
        """
        # 完整的德州扑克规则系统提示
        poker_rules = """
【德州扑克完整规则】

一、游戏流程
1. 每位玩家发2张底牌(hole cards)，只有自己可见
2. 游戏共4个下注轮：
   - 翻牌前(Pre-flop): 发底牌后，大盲左侧先行动
   - 翻牌(Flop): 发3张公共牌后下注
   - 转牌(Turn): 发第4张公共牌后下注
   - 河牌(River): 发第5张公共牌后下注
3. 最终用5张最佳组合(2张底牌+5张公共牌中选5张)比大小

二、牌型大小(从大到小)
1. 皇家同花顺(Royal Flush): A-K-Q-J-10同花色，最强牌型
2. 同花顺(Straight Flush): 5张同花色连续牌，如5♥6♥7♥8♥9♥
3. 四条(Four of a Kind): 4张相同点数，如9♠9♦9♥9♣
4. 葫芦(Full House): 三条+一对，如KKK22
5. 同花(Flush): 5张同花色非连续牌
6. 顺子(Straight): 5张连续点数不同花色，A可作最大或最小(A2345或10JQKA)
7. 三条(Three of a Kind): 3张相同点数
8. 两对(Two Pair): 两组对子
9. 一对(One Pair): 一组对子
10. 高牌(High Card): 无以上牌型，比最大单牌

三、位置说明(顺时针)
- BTN(庄家/按钮): 翻牌后最后行动，信息优势最大
- SB(小盲注): 庄家左边第一位，强制下小盲
- BB(大盲注): 小盲左边，强制下大盲(=2倍小盲)
- UTG(枪口位): 大盲左边，翻牌前最先行动，位置最差
- MP(中间位): 中间位置
- CO(关煞位): 庄家右边，位置仅次于庄家
位置越靠后越有利，因为能看到更多对手行动后再决策

四、下注规则
- 过牌(Check): 无人下注时，不投入筹码传递行动权
- 下注(Bet): 本轮第一个投入筹码
- 跟注(Call): 投入与前面下注相同的筹码
- 加注(Raise): 增加下注额，最小加注=前次加注幅度
- 全押(All-in): 投入全部筹码
- 弃牌(Fold): 放弃本局，已投入筹码归底池

五、加注规则(无限注)
- 最小加注额 = 上一次加注的增加额
- 例: 盲注50/100，A加注到300(增加200)，B再加注至少到500(再增加200)
- 无最大限制，可随时All-in

六、底池赔率与期望值
- 底池赔率 = 需跟注额 / (底池+需跟注额)
- 若你的胜率 > 底池赔率，则跟注有正期望值
- 例: 底池1000，需跟注200，底池赔率=200/1200=16.7%，胜率>16.7%应跟注

七、常见起手牌强度
- 超强: AA, KK, QQ, AKs
- 强牌: JJ, TT, AK, AQs, AJs
- 中强: 99-77, KQs, ATs, KJs
- 可玩: 中小对子, 同花连牌(如76s,87s), Axs

八、基本策略原则
1. 位置优势: 后位可玩更多牌，前位要收紧
2. 紧凶风格(TAG): 精选起手牌，进入底池就主动加注
3. 控制底池: 弱牌小底池，强牌大底池
4. 读取对手: 根据下注模式判断对手牌力范围
5. 避免沉没成本: 已投入筹码不应影响当前决策

九、翻牌前参与度指南
- 不要过度弃牌！扑克需要参与才有乐趣
- 超强牌(AA/KK/QQ/AK): 100%加注，绝不弃牌
- 强牌(JJ/TT/AQ/AJs): 90%以上加注或跟注
- 中等牌(99-77/KQs/ATs): 70%参与，后位更积极
- 可玩牌(小对子/同花连张/Axs): 后位50%参与
- 大盲位：加注不大时多跟注看翻牌
- 记住：弃太多牌=被偷太多盲注=输钱！
"""

        system_content = f"""{poker_rules}

【你的角色设定】
你是德州扑克玩家【{self.config['name']}】。
性格特点：{self.config.get('persona', '')}
风险偏好：{self.config.get('risk_profile', 'balanced')}

【重要：积极参与游戏！】
- 这是娱乐游戏，不要总是弃牌！
- 翻牌前有合理的起手牌就应该参与
- 大盲位加注小时要保护盲注，跟注看翻牌
- 后位(BTN/CO)要更积极地加注和跟注
- 记住：过度弃牌 = 被偷盲注 = 必输！

【对话策略】
桌上的对话会影响对手的心理和决策，善用<speech>来虚张声势、误导或干扰对手。每轮都要说话！

【重要规则】
1. <speech>中绝对不能透露你的具体手牌！不能说"我有AA"、"我拿了对子"等。可以暗示强弱但绝不能明说！
2. 严格用 <thinking>、<action>、<speech> XML 格式回复。
3. 认真参考【行动建议】做决策，不要随意弃牌！"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        full = ""

        if on_chunk:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=600,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full += delta
                    on_chunk(self.player.id, delta)
        else:
            resp = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=600,
                stream=False,
            )
            full = resp.choices[0].message.content or ""

        return full

    def update_memory(self, won: bool, amount: float):
        self.memory.record_result(won, amount)

    def observe_opponent(self, opponent_id: str, action_type: str, context: dict):
        self.memory.get_opponent_profile(opponent_id).update(action_type, context)
