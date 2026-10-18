import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { clearError, login, register } from '../../store/authSlice';
import { Brand, Icon, ModeBadge } from './Club';
import { Card } from '../Card';

export default function AuthPage({ registering = false }: { registering?: boolean }) {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, isLoading, error } = useSelector((s: RootState) => s.auth);
  const [username, setUsername] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false); const [validation, setValidation] = useState('');
  useEffect(() => { if (isAuthenticated) navigate('/', { replace: true }); }, [isAuthenticated, navigate]);
  useEffect(() => () => { dispatch(clearError()); }, [dispatch]);
  const submit = (e: React.FormEvent) => {
    e.preventDefault(); setValidation('');
    if (registering && password !== confirm) { setValidation('两次输入的密码不一致'); return; }
    if (registering) dispatch(register({ username, email, password })); else dispatch(login({ username, password }));
  };
  const message = validation || error;
  return <main className="club-auth">
    <section className="club-auth-story"><Brand /><div className="club-auth-editorial"><span className="club-eyebrow">A SEAT AT THE TABLE</span><h1>每一手牌，<br />都有新的<span>可能。</span></h1><p>坐下来，与不同风格的 AI 对手过招。<br />在每一次决策里，找到自己的节奏。</p><div className="club-auth-art" aria-hidden="true"><div className="club-orbit" /><div className="club-art-card art-card-one"><Card rank={14} suit={0} /></div><div className="club-art-card art-card-two"><Card rank={13} suit={1} /></div><div className="club-art-chip chip-one" /><div className="club-art-chip chip-two" /><span className="club-art-suit">♠</span></div></div><footer className="club-auth-foot"><span>TEXAS HOLD’EM</span><span>纯模拟筹码 · 无现金交易</span></footer></section>
    <section className="club-auth-main"><div className="club-auth-top"><Link to="/" className="club-text-link"><Icon name="back" />返回大厅</Link><ModeBadge /></div><div className="club-auth-form-wrap"><span className="club-eyebrow">WELCOME TO THE CLUB</span><h2>{registering ? '为你，留一个座位。' : '欢迎回到牌桌。'}</h2><p className="club-muted">{registering ? '创建账户，开始你的扑克之旅。' : '登录账户，继续你的下一手。'}</p>
      <form onSubmit={submit} className="club-form">{message && <div className="club-alert" role="alert">{message}</div>}
      <label>用户名<input name="username" autoComplete="username" required minLength={registering ? 3 : undefined} maxLength={50} placeholder={registering ? '起一个牌桌上的名字' : '输入你的用户名'} value={username} onChange={e => setUsername(e.target.value)} /></label>
      {registering && <label>邮箱<input name="email" type="email" autoComplete="email" required placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} /></label>}
      <label>密码<div className="club-password"><input name="password" type={showPassword ? 'text' : 'password'} autoComplete={registering ? 'new-password' : 'current-password'} required minLength={registering ? 6 : undefined} maxLength={100} placeholder={registering ? '至少 6 个字符' : '输入你的密码'} value={password} onChange={e => setPassword(e.target.value)} /><button type="button" aria-label={showPassword ? '隐藏密码' : '显示密码'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}><Icon name="eye" /></button></div></label>
      {registering && <label>确认密码<input name="confirmPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required placeholder="再次输入密码" value={confirm} onChange={e => setConfirm(e.target.value)} /></label>}
      <button className="club-btn club-btn-gold club-btn-wide" type="submit" disabled={isLoading}>{isLoading ? '正在处理…' : registering ? '创建账户' : '登录牌桌'}{!isLoading && <Icon name="arrow" />}</button></form>
      <p className="club-auth-switch">{registering ? '已经有账户？' : '第一次来到这里？'} <Link to={registering ? '/login' : '/register'}>{registering ? '前往登录' : '创建账户'}</Link></p><div className="club-divider"><span>或者，先试一手</span></div><Link className="club-btn club-btn-outline club-btn-wide" to="/">以游客身份体验<Icon name="arrow" /></Link><p className="club-auth-note">游客无需注册，即可进入模拟牌局。</p>
    </div><footer className="club-auth-bottom">一张牌桌，无数种可能。</footer></section>
  </main>;
}
