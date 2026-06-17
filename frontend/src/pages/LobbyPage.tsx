import React, { useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { motion } from "framer-motion";
import { API_BASE_URL } from "../config";
import { RootState, AppDispatch } from "../store";
import { logout } from "../store/authSlice";

// ─── 全部 15 个 AI Agent ─────────────────────────────────────────────────
const AGENT_OPTIONS = [
  { id: "laowang",  name: "老王",     difficulty: "easy",   style: "超级保守",  desc: "只打强牌，极少虚张声势" },
  { id: "dushen",   name: "赌神",     difficulty: "hard",   style: "极度激进",  desc: "频繁大注施压，永不服输" },
  { id: "jiaoshou", name: "教授",     difficulty: "medium", style: "数学分析",  desc: "精通概率论，理性决策" },
  { id: "xiaoli",   name: "小李",     difficulty: "easy",   style: "随机不稳",  desc: "决策不稳定，容易被激将" },
  { id: "pukelian", name: "扑克脸",   difficulty: "medium", style: "欺骗型",    desc: "擅长 Bluff，误导对手" },
  { id: "meimei",   name: "美美",     difficulty: "easy",   style: "社交型",    desc: "享受游戏氛围，打牌开心" },
  { id: "luobo",    name: "萝卜头",   difficulty: "easy",   style: "位置意识",  desc: "后位激进，前位谨慎" },
  { id: "laohu",    name: "老虎",     difficulty: "medium", style: "紧凶型",    desc: "精选起手牌，强势出击" },
  { id: "xiaoming", name: "小明",     difficulty: "easy",   style: "跟注站",    desc: "喜欢看牌，难被吓跑" },
  { id: "nvwang",   name: "女王",     difficulty: "hard",   style: "读牌高手",  desc: "擅长分析对手行为" },
  { id: "guanjun",  name: "世界冠军", difficulty: "hard",   style: "全能型",    desc: "三届金手链，深不可测" },
  { id: "wangzhe",  name: "网络之王", difficulty: "hard",   style: "GTO机器",   desc: "多桌碾压，数学最优" },
  { id: "kuangmo",  name: "狂魔",     difficulty: "medium", style: "超级激进",  desc: "疯狂进攻，500万粉主播" },
  { id: "lengxue",  name: "冷血",     difficulty: "hard",   style: "精算剥削",  desc: "冷酷无情，漏洞猎手" },
  { id: "laoqian",  name: "千王",     difficulty: "medium", style: "心理操控",  desc: "微表情大师，读心专家" },
];

const DIFFICULTY_OPTIONS = [
  { value: "easy",    label: "简单" },
  { value: "medium",  label: "中等" },
  { value: "hard",    label: "困难" },
  { value: "mixed",   label: "混合" },
];

const THEME_OPTIONS = [
  { value: "balanced",          label: "均衡桌" },
  { value: "aggressive",        label: "激进桌" },
  { value: "beginner_friendly", label: "新手友好" },
  { value: "random",            label: "随机" },
];

// ─── 动态座位位置生成 ───────────────────────────────────────
// 在椭圆上均匀分布 n 个座位，玩家固定在底部中间 (seat 0)
function generateSeatPositions(n: number) {
  const positions = [];
  for (let i = 0; i < n; i++) {
    // 玩家在下，AI 在上方均匀分布
    // 角度：从右边开始顺时针 (0=right, 90=bottom, 180=left, 270=top)
    const angleDeg = 90 + (i * 360) / n;
    const angleRad = (angleDeg * Math.PI) / 180;

    // 椭圆参数：水平半径 42%，垂直半径 38%
    const rx = 42;
    const ry = 38;
    const cx = 50;
    const cy = 50;

    const left = cx + rx * Math.cos(angleRad);
    const top = cy + ry * Math.sin(angleRad);

    positions.push({
      top: `${top}%`,
      left: `${left}%`,
      transform: "translate(-50%, -50%)",
    });
  }
  return positions;
}

type SeatOccupant = { type: "player"; name: string } | { type: "agent"; agentId: string } | null;

export const LobbyPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { user, isAuthenticated, isLoading: authLoading } = useSelector((state: RootState) => state.auth);
  const [playerName, setPlayerName] = useState(user?.username || "Player");

  // ─── 新增状态：牌桌配置 ───
  const [tableSize, setTableSize] = useState(6);
  const [aiFillEnabled, setAiFillEnabled] = useState(true);
  const [difficultyLevel, setDifficultyLevel] = useState("mixed");
  const [personaTheme, setPersonaTheme] = useState("balanced");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 动态座位位置
  const seatPositions = useMemo(() => generateSeatPositions(tableSize), [tableSize]);

  // 初始化/更新 seats 当 tableSize 变化时
  const [seats, setSeats] = useState<SeatOccupant[]>(() => {
    const initial: SeatOccupant[] = Array(6).fill(null);
    initial[0] = { type: "player", name: user?.username || "Player" };
    return initial;
  });

  // 当 tableSize 变化时重新设置 seats 数组大小
  React.useEffect(() => {
    setSeats(prev => {
      if (prev.length === tableSize) return prev;
      const newSeats: SeatOccupant[] = Array(tableSize).fill(null);
      // 保留玩家位置和已有的 agent
      newSeats[0] = { type: "player", name: playerName };
      for (let i = 1; i < Math.min(prev.length, tableSize); i++) {
        if (prev[i]?.type === "agent") {
          newSeats[i] = prev[i];
        }
      }
      return newSeats;
    });
  }, [tableSize]);

  const [selectedAgentForSeat, setSelectedAgentForSeat] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Require authentication to access lobby
  React.useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Update player name when user logs in
  React.useEffect(() => {
    if (user?.username) {
      setPlayerName(user.username);
      setSeats(prev => prev.map(s => s?.type === "player" ? { ...s, name: user.username } : s));
    }
  }, [user?.username]);

  // 获取已使用的 agent ids
  const usedAgentIds = seats
    .filter((s): s is { type: "agent"; agentId: string } => s?.type === "agent")
    .map(s => s.agentId);

  // 根据难度筛选可见的 AI
  const filteredAgents = useMemo(() => {
    if (!showAdvanced || aiFillEnabled) return [];
    if (difficultyLevel === "mixed") return AGENT_OPTIONS;
    return AGENT_OPTIONS.filter(a => a.difficulty === difficultyLevel);
  }, [difficultyLevel, showAdvanced, aiFillEnabled]);

  // 计算自动补位预览
  const autoFillCount = aiFillEnabled ? tableSize - 1 - usedAgentIds.length : 0;

  const getAgentInfo = (agentId: string) => AGENT_OPTIONS.find(a => a.id === agentId);

  // Show loading while checking auth
  if (authLoading || !isAuthenticated) {
    return (
      <div className="h-screen w-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-500"></div>
      </div>
    );
  }

  // 点击座位
  const handleSeatClick = (seatIndex: number) => {
    if (aiFillEnabled) return; // 自动补位模式下不允许手动操作座位

    const current = seats[seatIndex];
    if (current?.type === "player") return;
    if (current?.type === "agent") {
      const newSeats = [...seats];
      newSeats[seatIndex] = null;
      setSeats(newSeats);
      return;
    }
    if (selectedAgentForSeat) {
      const newSeats = [...seats];
      newSeats[seatIndex] = { type: "agent", agentId: selectedAgentForSeat };
      setSeats(newSeats);
      setSelectedAgentForSeat(null);
    }
  };

  // 移动玩家到指定座位
  const movePlayerToSeat = (targetSeatIndex: number) => {
    if (aiFillEnabled) return;
    const playerSeatIndex = seats.findIndex(s => s?.type === "player");
    if (playerSeatIndex === targetSeatIndex) return;
    const newSeats = [...seats];
    const targetOccupant = newSeats[targetSeatIndex];
    newSeats[targetSeatIndex] = { type: "player", name: playerName };
    newSeats[playerSeatIndex] = targetOccupant;
    setSeats(newSeats);
  };

  // 更新玩家名称
  const handleNameChange = (name: string) => {
    setPlayerName(name);
    const newSeats = seats.map(s =>
      s?.type === "player" ? { ...s, name } : s
    );
    setSeats(newSeats);
  };

  // 随机分配AI到座位
  const handleRandomAssign = () => {
    if (aiFillEnabled) return;
    const newSeats: SeatOccupant[] = [...seats];
    const emptySeats: number[] = [];
    newSeats.forEach((seat, idx) => {
      if (!seat) emptySeats.push(idx);
    });
    const unusedAgents = AGENT_OPTIONS.filter(a => !usedAgentIds.includes(a.id));
    const shuffledAgents = [...unusedAgents].sort(() => Math.random() - 0.5);
    const shuffledSeats = [...emptySeats].sort(() => Math.random() - 0.5);
    const assignCount = Math.min(shuffledAgents.length, shuffledSeats.length);
    for (let i = 0; i < assignCount; i++) {
      newSeats[shuffledSeats[i]] = { type: "agent", agentId: shuffledAgents[i].id };
    }
    setSeats(newSeats);
    setSelectedAgentForSeat(null);
  };

  // 清空所有AI
  const handleClearAll = () => {
    if (aiFillEnabled) return;
    const newSeats = seats.map(s => s?.type === "player" ? s : null);
    setSeats(newSeats);
    setSelectedAgentForSeat(null);
  };

  // ─── Quick Play ───────────────────────────────────────────
  const handleQuickPlay = async () => {
    setIsLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/games`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_name: playerName,
          table_size: 6,
          ai_fill_enabled: true,
          ai_difficulty_level: "mixed",
          ai_persona_theme: "balanced",
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "创建游戏失败");
      }
      const data = await res.json();
      navigate("/game/" + data.gameId);
    } catch (e: any) {
      setError(e.message || "无法连接服务器，请确保后端已启动");
    } finally {
      setIsLoading(false);
    }
  };

  const handleStart = async () => {
    // 自动补位模式：不需要手动选AI
    if (aiFillEnabled) {
      if (tableSize < 2) {
        setError("牌桌大小至少为 2");
        return;
      }
      setIsLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE_URL}/api/games`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_name: playerName,
            table_size: tableSize,
            ai_fill_enabled: true,
            ai_difficulty_level: difficultyLevel,
            ai_persona_theme: personaTheme,
          }),
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "创建游戏失败");
        }
        const data = await res.json();
        navigate("/game/" + data.gameId);
      } catch (e: any) {
        setError(e.message || "无法连接服务器，请确保后端已启动");
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 手动模式
    const agentSeats = seats
      .map((s, idx) => (s?.type === "agent" ? { seatIndex: idx, agentId: s.agentId } : null))
      .filter((s): s is { seatIndex: number; agentId: string } => s !== null);

    if (agentSeats.length < 1) {
      setError("请至少选择1个 AI 对手，或开启自动补位");
      return;
    }

    const playerSeatIndex = seats.findIndex(s => s?.type === "player");
    setIsLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/games`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_name: playerName,
          agent_ids: agentSeats.map(s => s.agentId),
          table_size: tableSize,
          ai_fill_enabled: false,
          seat_arrangement: {
            player_seat: playerSeatIndex,
            agent_seats: agentSeats.map(s => ({ seat: s.seatIndex, agent_id: s.agentId })),
          },
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "创建游戏失败");
      }
      const data = await res.json();
      navigate("/game/" + data.gameId);
    } catch (e: any) {
      setError(e.message || "无法连接服务器，请确保后端已启动");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-gray-950 overflow-hidden flex flex-col safe-area-container">
      {/* Auth Header */}
      <div className="absolute top-2 right-2 sm:top-4 sm:right-4 z-10 flex items-center gap-2">
        {isAuthenticated && user ? (
          <>
            <span className="text-gray-400 text-xs hidden sm:inline">
              {user.username}
            </span>
            <Link
              to="/profile"
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs sm:text-sm rounded-lg transition-colors"
            >
              Profile
            </Link>
            {user.role !== 'user' && (
              <Link
                to="/admin"
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs sm:text-sm rounded-lg transition-colors"
              >
                Admin
              </Link>
            )}
            <button
              onClick={() => dispatch(logout())}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs sm:text-sm rounded-lg transition-colors"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link
              to="/login"
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs sm:text-sm rounded-lg transition-colors"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs sm:text-sm rounded-lg transition-colors"
            >
              Register
            </Link>
          </>
        )}
      </div>

      <motion.div
        className="flex-1 flex flex-col overflow-hidden p-2 sm:p-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Title */}
        <div className="text-center mb-1 sm:mb-2 flex-shrink-0">
          <h1 className="text-yellow-400 font-mono text-lg sm:text-2xl font-bold tracking-wider">
            POKER LLM
          </h1>
          <p className="text-gray-500 text-[10px] sm:text-xs mt-1 font-mono hidden sm:block">
            {aiFillEnabled
              ? "AI 将自动补位填满牌桌，点击 START 开始游戏"
              : "关闭自动补位后手动选择 AI，点击座位放置"}
          </p>
        </div>

        {/* ─── 配置栏 ─── */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2 flex-shrink-0 justify-center">
          {/* 牌桌大小 */}
          <div className="flex items-center gap-1">
            <label className="text-gray-400 text-[10px] sm:text-xs font-mono whitespace-nowrap">桌人数:</label>
            <select
              value={tableSize}
              onChange={e => setTableSize(Number(e.target.value))}
              className="bg-gray-800 text-white border border-gray-600 rounded px-1.5 py-1 font-mono text-xs sm:text-sm focus:outline-none focus:border-yellow-500"
            >
              {[2, 3, 4, 5, 6, 7, 8, 9].map(n => (
                <option key={n} value={n}>{n}人</option>
              ))}
            </select>
          </div>

          {/* 自动补位开关 */}
          <div className="flex items-center gap-1">
            <label className="text-gray-400 text-[10px] sm:text-xs font-mono whitespace-nowrap">自动补位:</label>
            <button
              onClick={() => setAiFillEnabled(!aiFillEnabled)}
              className={`w-9 h-5 sm:w-10 sm:h-6 rounded-full relative transition-colors ${
                aiFillEnabled ? "bg-green-500" : "bg-gray-600"
              }`}
            >
              <div
                className={`w-4 h-4 sm:w-5 sm:h-5 bg-white rounded-full absolute top-0.5 transition-transform ${
                  aiFillEnabled ? "translate-x-4 sm:translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {/* 难度选择 */}
          <div className="flex items-center gap-1">
            <label className="text-gray-400 text-[10px] sm:text-xs font-mono whitespace-nowrap">难度:</label>
            <select
              value={difficultyLevel}
              onChange={e => setDifficultyLevel(e.target.value)}
              className="bg-gray-800 text-white border border-gray-600 rounded px-1.5 py-1 font-mono text-xs sm:text-sm focus:outline-none focus:border-yellow-500"
            >
              {DIFFICULTY_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* 主题选择 */}
          <div className="flex items-center gap-1">
            <label className="text-gray-400 text-[10px] sm:text-xs font-mono whitespace-nowrap">主题:</label>
            <select
              value={personaTheme}
              onChange={e => setPersonaTheme(e.target.value)}
              className="bg-gray-800 text-white border border-gray-600 rounded px-1.5 py-1 font-mono text-xs sm:text-sm focus:outline-none focus:border-yellow-500"
            >
              {THEME_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* 高级模式切换 */}
          {!aiFillEnabled && (
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                showAdvanced ? "bg-cyan-700 text-cyan-200" : "bg-gray-700 text-gray-400"
              }`}
            >
              {showAdvanced ? "隐藏AI面板" : "手动选AI"}
            </button>
          )}
        </div>

        {/* 主内容区域 */}
        <div className="flex-1 flex flex-col sm:flex-row gap-2 sm:gap-4 overflow-hidden min-h-0">
          {/* Left: 牌桌座位图 */}
          <div className="flex-1 bg-gray-900 border border-gray-700 rounded-xl p-2 sm:p-4 flex flex-col min-h-0 overflow-hidden">
            <div className="flex items-center justify-between mb-1 sm:mb-2 flex-shrink-0">
              <label className="text-gray-400 text-[10px] sm:text-xs font-mono">
                TABLE ({tableSize}人) — {aiFillEnabled ? `自补 ${autoFillCount > 0 ? autoFillCount : 0} AI` : `${usedAgentIds.length + 1} 玩家`}
              </label>
              {!aiFillEnabled && (
                <div className="flex gap-1">
                  <button
                    onClick={handleRandomAssign}
                    className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white flex items-center justify-center transition-all active:scale-95"
                    title="随机分配"
                  >
                    <span className="text-sm sm:text-lg">&#127922;</span>
                  </button>
                  <button
                    onClick={handleClearAll}
                    className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 flex items-center justify-center transition-all active:scale-95"
                    title="清空"
                  >
                    <span className="text-xs sm:text-sm">&#10005;</span>
                  </button>
                </div>
              )}
            </div>

            {/* 牌桌 */}
            <div className="flex-1 relative min-h-0">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-full h-full max-w-md max-h-[200px] sm:max-h-none aspect-[16/10]">
                  {/* 桌面 */}
                  <div
                    className="absolute inset-[15%] rounded-[50%] border-4 border-yellow-900"
                    style={{
                      background: "radial-gradient(ellipse at center, #2e7d32 0%, #1b5e20 70%, #0a3d0a 100%)",
                    }}
                  />

                  {/* 座位 */}
                  {seatPositions.map((pos, idx) => {
                    const occupant = seats[idx];
                    const isPlayer = occupant?.type === "player";
                    const isAgent = occupant?.type === "agent";
                    const agentInfo = isAgent ? getAgentInfo(occupant.agentId) : null;
                    const isEmpty = !occupant;
                    const isHighlighted = !aiFillEnabled && isEmpty && selectedAgentForSeat;

                    return (
                      <div
                        key={idx}
                        className="absolute"
                        style={{ top: pos.top, left: pos.left, transform: pos.transform }}
                      >
                        <button
                          onClick={() => {
                            if (aiFillEnabled) return;
                            if (isPlayer) return;
                            if (isEmpty && !selectedAgentForSeat) return;
                            handleSeatClick(idx);
                          }}
                          onDoubleClick={() => {
                            if (aiFillEnabled) return;
                            if (!isPlayer && !isEmpty) movePlayerToSeat(idx);
                          }}
                          className={`
                            w-9 h-9 sm:w-12 sm:h-12 rounded-full border-2 flex flex-col items-center justify-center
                            transition-all text-[7px] sm:text-xs font-mono
                            ${isPlayer
                              ? "bg-yellow-600 border-yellow-400 text-white cursor-default"
                              : isAgent
                                ? "bg-cyan-900 border-cyan-500 text-cyan-200"
                                : aiFillEnabled
                                  ? "bg-purple-900/50 border-purple-700/50 text-purple-400"
                                  : isHighlighted
                                    ? "bg-green-900 border-green-400 text-green-300 animate-pulse cursor-pointer"
                                    : "bg-gray-800 border-gray-600 text-gray-500"
                            }
                          `}
                          title={
                            isPlayer ? "你的座位"
                            : isAgent ? `${agentInfo?.name}`
                            : aiFillEnabled ? `AI 自动补位 #${idx + 1}`
                            : selectedAgentForSeat ? "点击放置 AI"
                            : "空座位"
                          }
                        >
                          {isPlayer ? (
                            <span className="text-[7px] sm:text-[10px]">YOU</span>
                          ) : isAgent ? (
                            <span className="text-[7px] sm:text-[10px] font-bold">{agentInfo?.name}</span>
                          ) : aiFillEnabled ? (
                            <span className="text-[10px] sm:text-sm">&#129302;</span>
                          ) : (
                            <span className="text-sm sm:text-lg">{idx + 1}</span>
                          )}
                        </button>
                      </div>
                    );
                  })}

                  {/* 自动补位指示器（桌面中央） */}
                  {aiFillEnabled && autoFillCount > 0 && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="bg-purple-900/80 border border-purple-500 rounded-lg px-2 py-1 sm:px-3 sm:py-1.5">
                        <span className="text-purple-300 text-[9px] sm:text-xs font-mono">
                          +{autoFillCount} AI
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 玩家名字输入 */}
            <div className="mt-2 flex-shrink-0">
              <div className="flex items-center gap-2">
                <label className="text-gray-400 text-[10px] sm:text-xs font-mono whitespace-nowrap">NAME:</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={e => handleNameChange(e.target.value)}
                  className="flex-1 bg-gray-800 text-white border border-gray-600 rounded px-2 py-1 font-mono text-xs sm:text-sm focus:outline-none focus:border-yellow-500"
                  maxLength={12}
                />
              </div>
            </div>
          </div>

          {/* Right: AI 选择面板（仅在手动模式+高级模式下显示） */}
          {!aiFillEnabled && showAdvanced && (
            <div className="w-full sm:w-64 lg:w-72 bg-gray-900 border border-gray-700 rounded-xl p-2 sm:p-4 flex flex-col min-h-0 overflow-hidden">
              <div className="flex items-center justify-between mb-1 sm:mb-2 flex-shrink-0">
                <label className="text-gray-400 text-[10px] sm:text-xs font-mono">
                  AI ({usedAgentIds.length}/{tableSize - 1})
                </label>
              </div>
              {selectedAgentForSeat && (
                <p className="text-green-400 text-[10px] sm:text-xs font-mono mb-1 flex-shrink-0">
                  &#8592; 点击空座位放置
                </p>
              )}

              <div className="flex-1 overflow-y-auto space-y-1 sm:space-y-2 min-h-0">
                {filteredAgents.map(agent => {
                  const isUsed = usedAgentIds.includes(agent.id);
                  const isSelected = selectedAgentForSeat === agent.id;
                  const diffColor = agent.difficulty === "easy" ? "text-green-400" : agent.difficulty === "medium" ? "text-yellow-400" : "text-red-400";

                  return (
                    <button
                      key={agent.id}
                      disabled={isUsed}
                      className={`
                        w-full flex items-center gap-2 px-2 py-1 sm:px-3 sm:py-2 rounded-lg border transition-all text-left
                        ${isUsed
                          ? "border-gray-700 bg-gray-800 opacity-50 cursor-not-allowed"
                          : isSelected
                            ? "border-green-500 bg-green-900 bg-opacity-30"
                            : "border-gray-700 bg-gray-800 hover:border-cyan-500"
                        }
                      `}
                      onClick={() => {
                        if (!isUsed) {
                          setSelectedAgentForSeat(isSelected ? null : agent.id);
                        }
                      }}
                    >
                      <div className={`
                        w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-[10px] sm:text-xs font-bold flex-shrink-0
                        ${isUsed ? "bg-gray-700 text-gray-500" : "bg-cyan-800 text-cyan-200"}
                      `}>
                        {agent.name[0]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1">
                          <span className="text-white font-bold text-[11px] sm:text-sm">{agent.name}</span>
                          <span className={`text-[8px] sm:text-[10px] font-mono ${diffColor}`}>
                            {agent.difficulty === "easy" ? "简单" : agent.difficulty === "medium" ? "中等" : "困难"}
                          </span>
                        </div>
                        <p className="text-gray-400 text-[8px] sm:text-[10px] truncate hidden sm:block">{agent.desc}</p>
                      </div>
                      {isUsed && <span className="text-green-400 text-[10px] sm:text-xs">&#10003;</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 自动补位信息面板 */}
          {aiFillEnabled && (
            <div className="w-full sm:w-56 lg:w-64 bg-gray-900 border border-gray-700 rounded-xl p-2 sm:p-4 flex flex-col justify-center min-h-0 overflow-hidden">
              <div className="text-center space-y-2 sm:space-y-3">
                <div className="text-purple-400 text-xl sm:text-3xl">&#129302;</div>
                <p className="text-gray-300 text-xs sm:text-sm font-mono">
                  自动补位已启用
                </p>
                <p className="text-gray-500 text-[10px] sm:text-xs">
                  系统将自动选择 {autoFillCount > 0 ? autoFillCount : tableSize - 1} 个 AI
                  填满 {tableSize} 人桌
                </p>
                <div className="bg-gray-800 rounded-lg p-2 space-y-1 text-left">
                  <div className="flex justify-between text-[10px] sm:text-xs">
                    <span className="text-gray-500">难度</span>
                    <span className="text-white">
                      {DIFFICULTY_OPTIONS.find(o => o.value === difficultyLevel)?.label}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] sm:text-xs">
                    <span className="text-gray-500">主题</span>
                    <span className="text-white">
                      {THEME_OPTIONS.find(o => o.value === personaTheme)?.label}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] sm:text-xs">
                    <span className="text-gray-500">总玩家</span>
                    <span className="text-yellow-400 font-bold">{tableSize}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <p className="text-red-400 text-xs font-mono mt-1 text-center flex-shrink-0">{error}</p>
        )}

        {/* Buttons */}
        <div className="flex gap-2 justify-center mt-2 flex-shrink-0">
          <button
            className={`
              px-4 py-2 sm:py-3 rounded-lg font-bold text-xs sm:text-base tracking-widest transition-all
              ${isLoading
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-500 text-white active:scale-95"
              }
            `}
            onClick={handleQuickPlay}
            disabled={isLoading}
          >
            {isLoading ? "LOADING..." : `QUICK PLAY (6P)`}
          </button>
          <button
            className={`
              px-6 py-2 sm:py-3 rounded-lg font-bold text-xs sm:text-base tracking-widest transition-all
              ${isLoading || (aiFillEnabled ? false : usedAgentIds.length < 1)
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-yellow-500 hover:bg-yellow-400 text-black active:scale-95"
              }
            `}
            onClick={handleStart}
            disabled={isLoading || (!aiFillEnabled && usedAgentIds.length < 1)}
          >
            {isLoading ? "LOADING..." : `START (${aiFillEnabled ? tableSize : usedAgentIds.length + 1}P)`}
          </button>
        </div>
      </motion.div>
    </div>
  );
};
