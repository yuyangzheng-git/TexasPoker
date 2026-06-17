# 快速开始指南

## 前置要求

- Python 3.11+
- Node.js 18+
- Anthropic API Key (Claude 访问权限)

## 1分钟快速启动

### 方式 A：一键启动脚本

```bash
cd /Users/2812019221qq.com/Poker_LLM_Agent_Game

# 编辑 .env 文件，填入你的 API Key
cp config/.env.example config/.env
vim config/.env  # 或用你喜欢的编辑器

# 运行启动脚本
bash start.sh
```

脚本会自动启动：
- ✓ Python 虚拟环境 + 后端服务
- ✓ npm 依赖安装 + 前端开发服务器
- ✓ 打开浏览器到 http://localhost:3000

### 方式 B：手动启动

**终端 1 - 后端**：
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../config/.env.example ../config/.env
# 编辑 .env 填入 API Key
uvicorn main:app --reload
```

**终端 2 - 前端**：
```bash
cd frontend
npm install
npm start
```

## 首次使用

1. **访问** http://localhost:3000
2. **输入** 你的玩家名字
3. **选择** 对手 AI (勾选 2-5 个)
4. **点击** "START GAME"
5. **操作** Fold/Call/Raise/All-in 按钮

## 后端 API 文档

启动后访问 http://localhost:8000/docs

### 主要端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/games` | 创建新游戏 |
| GET | `/api/games/{id}` | 获取游戏状态 |
| WebSocket | `/ws/{gameId}` | 实时游戏流 |

## 运行测试

```bash
bash run_tests.sh
```

会运行：
- ✓ 手牌评估测试 (21种组合)
- ✓ 边池计算测试
- ✓ Monte Carlo 胜率测试

## 项目结构

```
backend/           - 游戏引擎 + LLM Agent
  ├── game_engine.py        # 核心游戏逻辑
  ├── hand_evaluator.py     # C(7,5) 手牌评估
  ├── monte_carlo_equity.py # MC 胜率计算
  ├── agent_engine.py       # Prompt 构建
  └── llm_agent.py          # Claude API 调用

frontend/          - React UI
  ├── components/           # UI 组件 (6个)
  ├── pages/                # 页面 (2个)
  ├── store/                # Redux 状态
  └── hooks/                # WebSocket Hook

config/            - 配置文件
  ├── agent_personas.json   # 5个 AI 人格
  ├── game_config.json      # 游戏规则
  └── .env.example

tests/             - 单元测试
  ├── test_hand_evaluator.py
  └── test_side_pot.py

algorithms/        - 算法文档
  ├── hand_evaluation.md
  ├── monte_carlo_equity.md
  ├── pot_odds_calculation.md
  └── ...

data/              - 数据文件
  └── preflop_equity_table.json  # 169种起手牌

docs/              - 项目文档
  ├── PRD_详细版.docx       # 完整功能文档
  └── websocket_protocol.md # 通信协议
```

## 常见问题

### Q: 后端启动出错 "ModuleNotFoundError"
A: 确保激活了虚拟环境，运行 `source venv/bin/activate`

### Q: 前端显示连接错误
A: 检查后端是否运行在 `localhost:8000`，查看浏览器控制台日志

### Q: API Key 报错
A: 确保 `config/.env` 中 `ANTHROPIC_API_KEY` 正确填入，无空格

### Q: Agent 思考很慢
A: 正常现象，首次 LLM 调用可能需要 3-5 秒，后续会缓存

## 开发建议

### 添加新的 Agent 人格

编辑 `config/agent_personas.json`，添加新条目：
```json
{
  "id": "my_agent",
  "name": "我的 AI",
  "style": "风格描述",
  "temperature": 0.5,
  "persona": "性格设定文本...",
  "vpip_target": [0.20, 0.30],
  "pfr_target": [0.15, 0.25],
  "risk_profile": "balanced"
}
```

### 自定义游戏规则

编辑 `config/game_config.json`：
- `small_blind` / `big_blind` - 盲注
- `default_stack` - 初始筹码
- `agent_timeout_ms` - Agent 思考时限
- `max_concurrent_llm_calls` - 最大并发 LLM 调用

### 调试 Agent 决策

所有 LLM 调用都会打印到后端控制台：
```
[14:23:45] Calling Claude API for agent_dushen
[14:23:48] Response: <thinking>...</thinking> <action>raise 150</action>
```

## 下一步

- [ ] 添加真人多人房间 (改为服务器驱动)
- [ ] 实现游戏回放 + 统计分析
- [ ] 集成 Redis 缓存优化
- [ ] 部署到云端 (Docker + Kubernetes)
- [ ] 前端暗黑主题优化
- [ ] 添加声音效果和动画

## 许可证

MIT

---

有问题？查看 `/docs/websocket_protocol.md` 或 `/algorithms/` 中的详细文档。
