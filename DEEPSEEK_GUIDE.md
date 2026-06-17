# DeepSeek V4 启动指南

## ⚡ 一键启动（推荐）

```bash
cd /Users/2812019221qq.com/Poker_LLM_Agent_Game
bash start.sh
```

## 📝 手动启动步骤

### 1️⃣ 配置环境变量

```bash
cd /Users/2812019221qq.com/Poker_LLM_Agent_Game
cp config/.env.example config/.env
```

.env 文件内容（已预配置）：
```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 2️⃣ 启动后端服务

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # 或 Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

✅ 后端运行在：http://localhost:8000
✅ API 文档：http://localhost:8000/docs

### 3️⃣ 启动前端服务（新终端）

```bash
cd frontend
npm install
npm start
```

✅ 前端运行在：http://localhost:3000

## 🎮 游戏界面

1. 打开 http://localhost:3000
2. 输入玩家名字
3. 勾选 AI 对手（推荐：赌神、教授、小李）
4. 点击 "START GAME"
5. 完成！开始对战 🎰

## 💡 AI 模型选择

项目已配置自动按阶段切换模型：

| 阶段 | 模型 | 原因 |
|------|------|------|
| Pre-Flop | deepseek-v4-flash | 快速决策，信息少 |
| Flop | deepseek-v4-flash | 快速响应 |
| Turn | deepseek-v4-pro | 需要更强推理 |
| River | deepseek-v4-pro | 最关键决策 |

**成本优势**：Flash 便宜但快速，Pro 贵但精准。自动分层可最大化性价比。

## 🔍 监控日志

后端会输出每个 Agent 的决策信息：

```
[赌神] phase=pre_flop model=deepseek-v4-flash
[教授] phase=flop model=deepseek-v4-flash
[小李] phase=turn model=deepseek-v4-pro
```

## ⚠️ 常见问题

**Q: 连接被拒绝**
```
ConnectionError: Cannot connect to host 127.0.0.1 port 8000
```
→ 检查后端是否成功启动

**Q: API Key 报错**
```
AuthenticationError: Incorrect API key provided
```
→ 检查 config/.env 中 DEEPSEEK_API_KEY 是否正确

**Q: 找不到 deepseek-v4-flash**
```
NotFoundError: model deepseek-v4-flash not found
```
→ 检查 DeepSeek 账户是否有权限，或尝试用其他模型名

**Q: 超时**
```
Timeout waiting for response
```
→ 调大 agent_timeout_ms，网络可能较慢

## 🚀 性能优化

如果 Agent 响应太慢，可改为只用 flash：

编辑 `config/game_config.json`:
```json
"phase_model_map": {
  "pre_flop": "deepseek-v4-flash",
  "flop": "deepseek-v4-flash",
  "turn": "deepseek-v4-flash",
  "river": "deepseek-v4-flash"
}
```

或如果成本不是问题，全用 pro：
```json
"default_model": "deepseek-v4-pro"
```

## 📊 成本估算

**DeepSeek V4 定价**（约）：
- Flash：输入 ¥0.5/百万 tokens，输出 ¥1.5/百万 tokens
- Pro：输入 ¥4/百万 tokens，输出 ¥12/百万 tokens

**单局成本**（6 AI + 4 阶段）：
- 全 Flash：~¥0.08/局
- Flash + Pro 混合：~¥0.15/局
- 全 Pro：~¥0.40/局

---

祝游戏愉快！🎰
