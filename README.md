# 德州扑克 LLM 多智能体游戏

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

**阶段**：PRD 详细设计完成，准备代码开发

**下一步**：
- [ ] Phase 1：游戏引擎开发
- [ ] Phase 2：LLM Agent 接入
- [ ] Phase 3：MC 股似率优化
- [ ] Phase 4：记忆系统
- [ ] Phase 5：完整集成测试

## 贡献指南

详见项目内文档

## 许可证

MIT
