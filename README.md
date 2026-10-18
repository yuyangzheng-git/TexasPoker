# 德州扑克 LLM 多智能体游戏 | Texas Hold'em LLM Multi-Agent Game

## 机制修复与运行说明

下注规则、底牌过滤、断线恢复、账户兼容性及部署配置的最新说明见 [牌局机制改进说明](docs/mechanics-upgrade.md)。实时协议见 [WebSocket 协议](docs/websocket_protocol.md)。以下旧版架构规划中的部分目录和技术选型尚未落地，请以实际代码和上述运行说明为准。

网页对局默认使用风格化本地策略 AI（无需 API 密钥），可通过 `POKER_AGENT_MODE=llm` 切换到已配置密钥的模型服务。生产部署见 [服务器部署说明](deploy/README.md)。

## English Overview

This project is a Texas Hold'em simulation platform with LLM-based agents, Monte Carlo equity estimation, and real-time decision visualization. I built it as a testbed for studying AI decision-making under uncertainty and comparing language-model reasoning with algorithmic baselines.

**Highlights**

- Headless game engine with full betting rules, side pots, and C(7,5) hand evaluation
- LLM agents with personas, memory, and opponent profiling (`backend/llm_agent.py`, `backend/agent_engine.py`)
- Monte Carlo equity calculator and pot-odds engine for mathematical baselines
- Reproducible benchmark harness: `scripts/benchmark.py` (no API keys needed for MC/random seats)
- Preliminary results: [docs/benchmark-results.md](docs/benchmark-results.md) | research framing: [research.md](research.md)

## 项目概述

每个 AI 玩家（和真人玩家）由独立的 LLM 驱动，具有独立的性格、策略风格和记忆。通过自然语言思考并做出游戏决策，展现真实的心理博弈。

## 项目文件夹结构

```
Poker_LLM_Agent_Game/
├── docs/                              # 文档
│   └── Poker_LLM_Agent_PRD_详细版.docx # 完整PRD文档（所有算法）
├── backend/                           # 后端代码
│   ├── game_engine/                   # 游戏引擎核心逻辑
│   │   ├── game_state.py             # 游戏状态管理
│   │   ├── betting_round.py          # 下注轮控制
│   │   ├── hand_evaluator.py         # 手牌评估
│   │   ├── side_pot_calculator.py    # 边池计算
│   │   └── winner_determination.py   # 赢家判定
│   ├── agent_engine/                  # Agent 引擎
│   │   ├── agent_manager.py          # Agent 管理和调度
│   │   ├── prompt_builder.py         # Prompt 动态构建
│   │   ├── response_parser.py        # LLM 输出解析
│   │   ├── memory_system.py          # Agent 记忆管理
│   │   └── opponent_profiler.py      # 对手分析
│   ├── calculation_engine/            # 计算引擎
│   │   ├── monte_carlo_equity.py     # MC 胜率计算
│   │   ├── pot_odds_calculator.py    # 底池赔率
│   │   └── hand_strength_analyzer.py # 手牌强度分析
│   ├── models/                        # 数据模型
│   │   ├── game.py
│   │   ├── player.py
│   │   ├── agent.py
│   │   └── action.py
│   ├── llm_client/                    # LLM API 接口
│   │   ├── claude_api.py             # Claude API 封装
│   │   └── response_handler.py       # 响应处理
│   ├── api/                           # REST API
│   │   ├── main.py
│   │   ├── routes.py
│   │   └── websocket_handler.py
│   └── requirements.txt               # Python 依赖
├── frontend/                          # 前端代码
│   ├── src/
│   │   ├── components/               # React 组件
│   │   │   ├── Table.tsx            # 牌桌组件
│   │   │   ├── PlayerSeat.tsx       # 玩家座位
│   │   │   ├── AgentThinking.tsx    # Agent 思考面板
│   │   │   ├── ActionPanel.tsx      # 操作面板
│   │   │   └── CommunityCards.tsx   # 公共牌显示
│   │   ├── pages/
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      # WebSocket 连接
│   │   │   ├── useGameState.ts      # 游戏状态管理
│   │   │   └── useMonteCarlo.ts     # MC 并行计算
│   │   ├── store/                   # Redux Store
│   │   ├── utils/
│   │   │   ├── cardFormatter.ts
│   │   │   ├── pokerRules.ts
│   │   │   └── animations.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── public/
│   ├── styles/                       # Tailwind CSS
│   ├── package.json
│   └── tsconfig.json
├── algorithms/                        # 算法文档和参考
│   ├── fisher_yates_shuffle.md       # 洗牌算法
│   ├── hand_evaluation.md            # 手牌评估
│   ├── monte_carlo_equity.md         # MC 胜率
│   ├── pot_odds_calculation.md       # 底池赔率
│   ├── opponent_profiling.md         # 对手分析
│   └── agent_prompting.md            # Prompt 工程
├── config/                            # 配置文件
│   ├── agent_personas.json           # Agent 人格配置
│   ├── game_config.json              # 游戏规则配置
│   ├── model_config.json             # LLM 模型配置
│   └── .env.example                  # 环境变量模板
├── tests/                             # 测试文件
│   ├── test_hand_evaluator.py
│   ├── test_side_pot.py
│   ├── test_monte_carlo.py
│   └── test_agent_parser.py
├── data/                              # 数据文件
│   ├── preflop_equity_table.json     # 起手牌胜率表
│   ├── game_history.db              # 游戏记录
│   └── agent_memories/              # Agent 记忆备份
└── README.md                          # 本文件

```

## 核心算法清单

- **Fisher-Yates 洗牌**：确保公平随机发牌
- **手牌评估（C(7,5)枚举）**：从7张牌中找最强5张
- **Monte Carlo 股似率**：并行5000次模拟，<100ms
- **底池赔率计算**：数学决策基础
- **对手行为分析**：VPIP、PFR、虚张声势率等
- **Agent Prompt 动态构建**：注入数学指标和对手分析
- **LLM 输出解析+降级**：容错处理
- **边池计算**：All-in 时的复杂赔付
- **Agent 记忆压缩**：防止 Token 爆炸

## 快速开始

### 后端设置
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端设置
```bash
cd frontend
npm install
npm start
```

### 环境配置
1. 复制 `config/.env.example` 为 `.env`
2. 配置 Claude API key
3. 配置数据库连接

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + Redux Toolkit |
| 后端 | FastAPI (Python 3.11) |
| 实时通信 | WebSocket (Socket.io) |
| LLM | Claude API (claude-haiku-4-5) |
| 缓存 | Redis |
| 数据库 | PostgreSQL |

## 文档导航

- **完整 PRD**：[docs/Poker_LLM_Agent_PRD_详细版.docx](docs/Poker_LLM_Agent_PRD_详细版.docx)
  - 包含所有核心算法伪代码
  - 数据模型定义
  - API 接口规范
  - WebSocket 通信协议

- **算法文档**：[algorithms/](algorithms/) 目录
  - 每个核心算法的独立说明文档

- **配置参考**：[config/](config/) 目录
  - Agent 人格参数
  - 游戏规则参数
  - LLM 模型选择

## 主要特点

1. **多 LLM Agent 系统**：每个 AI 有独立人格和记忆
2. **透明决策过程**：实时展示 AI 的思考流程
3. **数学驱动**：基于 Monte Carlo 和底池赔率的客观决策
4. **对手建模**：持续追踪对手行为模式
5. **流式交互**：LLM 输出实时流到前端

## 项目状态

**阶段**：核心系统已完成，可用作研究测试平台。

- ✅ 游戏引擎（下注轮、边池、赢家判定）
- ✅ 手牌评估（C(7,5) 枚举）
- ✅ Monte Carlo 胜率计算
- ✅ LLM Agent（人格、记忆、对手画像、降级容错）
- ✅ WebSocket 实时对局 + React 前端
- ✅ 无头基准测试脚本（`scripts/benchmark.py`）
- 🔬 进行中：LLM vs 算法基线的大规模基准对比（见 [research.md](research.md)）

## Architecture | 系统架构

```
┌──────────────┐  WebSocket/REST  ┌───────────────────────────────┐
│  frontend/   │ ◄──────────────► │          backend/            │
│  React +     │                  │  main.py (FastAPI + WS)      │
│  Redux       │                  │    ├── game_engine.py        │  发牌/下注/边池/赢家
│              │                  │    ├── hand_evaluator.py     │  C(7,5) 手牌评估
└──────────────┘                  │    ├── monte_carlo_equity.py │  MC 胜率估算
                                  │    ├── llm_agent.py          │  LLM 决策 + 解析降级
                                  │    ├── agent_engine.py       │  记忆/对手画像/底池赔率
                                  │    └── deepseek_client.py    │  DeepSeek API
                                  └───────────────┬───────────────┘
                                                  │
                                  ┌───────────────▼───────────────┐
                                  │  config/  agent_personas.json │
                                  │           game_config.json    │
                                  └───────────────────────────────┘
```

## Benchmark | 基准测试

无需 API Key 即可对比 MC 基线 vs 随机对照：

```bash
# 100 手牌 × 3 随机种子，3 个 MC 基线席位 vs 3 个随机对照席位
# 庄家每手轮转自然平衡位置；--rotate 按种子轮换初始座位排布；
# --require-position-coverage 校验每种策略覆盖全部 6 个位置
python3 scripts/benchmark.py --hands 100 --sims 500 --seeds 42,43,44 \
    --rotate --require-position-coverage --rebuy --csv data/benchmark_results.csv

# 加入 LLM 席位（需要 ANTHROPIC_API_KEY 与 openai 包）
# 初始化失败默认终止实验；--llm-fallback 显式降级为 MC 基线（CSV 会标记 mc_fallback）
python3 scripts/benchmark.py --hands 100 --seeds 42,43,44 \
    --seats llm,llm,llm,mc,mc,mc --csv data/benchmark_llm_results.csv
```

结果与分析见 [docs/benchmark-results.md](docs/benchmark-results.md)。
当前结果仅对比两个算法基线，属于初步验证（非 LLM 决策质量结论）。

## Tests | 测试

```bash
./run_tests.sh        # 全部测试（手牌评估、边池、蒙特卡洛牌组、根目录导入、基准统计轨迹）
```

## My Contribution

Solo project (Yu Yang Zheng). What I designed and implemented:

- The game engine: betting-round control, side-pot calculation, winner determination
- C(7,5) hand evaluation and the Monte Carlo equity calculator
- The LLM agent stack: dynamic prompt building, response parsing with rule validation
  and fallback actions, memory compression, and opponent profiling (VPIP/PFR tracking)
- The WebSocket game server and the React table UI with agent-thinking visualization
- The headless benchmark harness (`scripts/benchmark.py`) with multi-seed runs,
  per-seed initial-alignment rotation, position recording, and per-decision
  fallback/token logging

What I fixed and verified in this repository (with automated checks):

- Hand-evaluator scoring: fixed cross-category overlap (e.g., four aces used to
  outrank a straight flush); 39 tests pass, including 7 cross-category/kicker cases
- Monte Carlo deck: known cards are now excluded from the simulation deck
  (`build_remaining_deck`; 47 cards with 5 known — regression-tested)
- Config paths are CWD-independent (`__file__`-based) across the import chain;
  tests import `agent_engine`/`llm_agent`/`main` from the repo root
- Position balancing: the old per-hand `--rotate` cancelled the dealer rotation
  and pinned each agent to one relative position (e.g. always CO). The run now
  records `position` and `dealer` per hand, verifies each strategy covers all
  six positions (`--require-position-coverage`), and rotates only the initial
  alignment per seed
- PFR counts pre-flop all-in raises (stack above the call price) but not
  all-in calls — tested through real engine hands
- The cross-seed summary shows per-seed values with a 95% t-confidence interval
  (NIST 1.3.5.2) instead of a normal-approximation CI
- Benchmark rigor: LLM seats bind the engine's real `Player` (state-sync tested),
  init failure aborts the run by default, and the CSV records the actual agent,
  fallback reasons (including init failures), and token usage
- Current `docs/benchmark-results.md` numbers are algorithmic-baseline sanity
  checks only (MC vs random; the 3-seed 95% t-CI includes zero); LLM
  comparisons are pending real API runs

## 服务器部署

生产环境部署与验收见 [deploy/README.md](deploy/README.md)。默认使用无需 API 密钥的本地策略 AI，前后端通过同源代理连接，账号与日志使用持久卷保存。

## 许可证

MIT
