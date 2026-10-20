import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { logout } from '../store/authSlice';
import { gameApi } from '../services/api';
import { ClubHeader, ModeBadge, Icon, useClub, PreferencesPanel, ClubDialog } from '../components/club/Club';
import { AGENT_OPTIONS } from '../components/club/agents';
import { Card } from '../components/Card';
import { cleanPlayerName, MAX_PLAYER_NAME } from '../utils/name';

export const LobbyPage: React.FC = () => {
  const navigate = useNavigate(); const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((s: RootState) => s.auth); const { localDemo } = useClub();
  const [name, setName] = useState(() => user?.username || sessionStorage.getItem('poker_guest_name') || '游客');
  const [size, setSize] = useState(6); const [difficulty, setDifficulty] = useState('mixed');
  const [theme, setTheme] = useState('balanced'); const [advanced, setAdvanced] = useState(false);
  const [selected, setSelected] = useState<string[]>([]); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [settings, setSettings] = useState(false);
  const begin = async () => {
    const playerName = cleanPlayerName(name);
    if (!playerName) { setError('先起一个牌桌上的名字。'); return; }
    setName(playerName); setBusy(true); setError('');
    try {
      sessionStorage.setItem('poker_guest_name', playerName);
      const result = await gameApi.createGame({ player_name: user?.username || playerName, table_size: size,
        ai_fill_enabled: true, ai_difficulty_level: difficulty, ai_persona_theme: theme,
        agent_ids: advanced ? selected : [] });
      navigate(`/game/${result.gameId}`);
    } catch (e) { setError((e as Error).message || '暂时无法创建牌局，请稍后重试。'); } finally { setBusy(false); }
  };
  const chooseSize = (n: number) => { setSize(n); setSelected(prev => prev.slice(0, n - 1)); };
  return <div className="club-page club-lobby"><ClubHeader><Link className="club-nav-link is-current" to="/">游戏大厅</Link><button className="club-icon-btn" aria-label="偏好设置" onClick={() => setSettings(!settings)}><Icon name="settings" /></button>{user ? <><Link className="club-account" to="/profile"><span className="club-avatar avatar-small">{user.username.slice(0, 1)}</span><span>{user.username}</span></Link>{user.role !== 'user' && <Link className="club-nav-link" to="/admin">管理</Link>}<button className="club-icon-btn" aria-label="退出登录" onClick={() => dispatch(logout())}><Icon name="logout" /></button></> : <Link className="club-btn club-btn-outline club-btn-small" to="/login">登录 / 注册</Link>}</ClubHeader>
    <main className="club-lobby-main"><section className="club-lobby-intro"><div><span className="club-eyebrow">YOUR NEXT HAND STARTS HERE</span><h1>好牌局，<br /><span>从这里开始。</span></h1><p>选一个座位，遇见不同风格的对手。<br />不必等待，下一手由你开启。</p></div><div className="club-lobby-art" aria-label="扑克主题插画"><div className="club-preview-felt"><span className="club-preview-wordmark">TEXAS<br /><small>POKER CLUB</small></span><div className="club-preview-cards"><Card rank={14} suit={0} /><Card rank={14} suit={1} /><Card faceDown /></div><span className="club-preview-chip" /><span className="club-preview-dealer">D</span></div><span className="club-art-caption">A LITTLE SKILL. A LITTLE LUCK.</span></div></section>
    <section className="club-lobby-bottom"><div className="club-table-setup"><div className="club-section-head"><div><span className="club-eyebrow">TAKE YOUR SEAT</span><h2>开启一场对局</h2></div><ModeBadge /></div><div className="club-setup-grid"><div><label className="club-field-label" htmlFor="player-name">牌桌昵称</label><input id="player-name" className="club-input" value={user?.username || name} disabled={!!user} maxLength={MAX_PLAYER_NAME} onChange={e => setName(e.target.value)} placeholder="大家该怎么称呼你？" /></div><fieldset className="club-size-field"><legend className="club-field-label">牌桌人数 <span>包含你</span></legend><div className="club-segment">{[2, 4, 6, 9].map(n => <button key={n} aria-pressed={size === n} className={size === n ? 'is-active' : ''} onClick={() => chooseSize(n)}>{n}<small>人</small></button>)}</div></fieldset></div>
      <div className="club-setup-summary"><span className="club-stack-icon"><Icon name="cards" /></span><div><strong>你与 {size - 1} 位 AI 对手</strong><p>{localDemo ? '本地算法决策 · 无需 API 密钥' : '独立 AI 对手 · 每手结束后可查看决策复盘'}</p></div><span className="club-badge">模拟筹码</span></div>
      <button className="club-advanced-toggle" aria-expanded={advanced} aria-controls="advanced-setup" onClick={() => setAdvanced(!advanced)}><span><Icon name="settings" />自定义对手</span><Icon name="chevron" /></button>
      {advanced && <div id="advanced-setup" className="club-advanced"><div className="club-setup-grid"><label className="club-field-label">难度<select className="club-input" value={difficulty} onChange={e => setDifficulty(e.target.value)}>{[['mixed','混合'],['easy','轻松'],['medium','标准'],['hard','挑战']].map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label><label className="club-field-label">对手风格<select className="club-input" value={theme} onChange={e => setTheme(e.target.value)}>{[['balanced','均衡桌'],['aggressive','激进桌'],['beginner_friendly','新手友好'],['random','随机']].map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label></div>{localDemo && <p className="club-help">对手根据所选角色的风格与难度，使用独立策略决策。</p>}<div className="club-agent-heading"><strong>指定角色</strong><span>已选 {selected.length} / {size - 1}，其余自动补位</span></div><div className="club-agent-picker">{AGENT_OPTIONS.map((agent, i) => <label className={`club-agent-choice ${selected.includes(agent.id) ? 'is-selected' : ''}`} key={agent.id}><input type="checkbox" checked={selected.includes(agent.id)} disabled={!selected.includes(agent.id) && selected.length >= size - 1} onChange={e => setSelected(prev => e.target.checked ? [...prev, agent.id] : prev.filter(id => id !== agent.id))} /><span className={`club-avatar avatar-tone-${i % 4}`}>{agent.name[0]}</span><span><strong>{agent.name}</strong><small>{agent.style}</small></span></label>)}</div></div>}
      {error && <div className="club-alert" role="alert">{error}</div>}<button className="club-btn club-btn-gold club-btn-wide club-start" disabled={busy} onClick={begin}>{busy ? '正在准备牌桌…' : '入座，开始游戏'}{!busy && <Icon name="arrow" />}</button><p className="club-fine-print">仅供游戏与策略练习，不涉及现金交易。</p>
    </div><aside className="club-lobby-guide"><span className="club-eyebrow">THE WAY WE PLAY</span><h2>每一次决策，<br />都值得回味。</h2><div className="club-guide-item"><span>01</span><div><h3>自己的节奏</h3><p>从双人切磋到九人牌桌，选择适合你的对局。</p></div></div><div className="club-guide-item"><span>02</span><div><h3>真实的博弈</h3><p>隐藏底牌、完整下注规则与独立对手决策。</p></div></div><div className="club-guide-item"><span>03</span><div><h3>看懂每一手</h3><p>本手结束后，回看行动记录与 AI 决策思路。</p></div></div><div className="club-guide-footer"><span>♠</span><p>牌有好坏，<br />每一手都有选择。</p></div></aside></section><footer className="club-lobby-footer"><span>TEXAS POKER CLUB</span><span>专注每一手，享受每一步。</span></footer></main>
    {settings && <ClubDialog title="按你的习惯来" onClose={() => setSettings(false)}><PreferencesPanel /><button className="club-btn club-btn-gold club-btn-wide" onClick={() => setSettings(false)}>完成</button></ClubDialog>}
  </div>;
};
