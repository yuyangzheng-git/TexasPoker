/**
 * Profile Page - User profile and statistics
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout, fetchUserStats } from '../store/authSlice';
import { authApi } from '../services/api';
import { AppDispatch, RootState } from '../store';
import { ClubHeader, Icon, PreferencesPanel, chips } from '../components/club/Club';
import { PasswordChangeRequest, UserUpdateRequest } from '../types/auth';

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { user, stats, isAuthenticated } = useSelector(
    (state: RootState) => state.auth
  );

  const [isEditing, setIsEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [editUsername, setEditUsername] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    dispatch(fetchUserStats());
  }, [isAuthenticated, navigate, dispatch]);

  useEffect(() => {
    if (user) {
      setEditUsername(user.username);
      setEditEmail(user.email);
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsLoading(true);

    try {
      const updateData: UserUpdateRequest = {};
      if (editUsername !== user?.username) updateData.username = editUsername;
      if (editEmail !== user?.email) updateData.email = editEmail;

      if (Object.keys(updateData).length === 0) {
        setIsEditing(false);
        setIsLoading(false);
        return;
      }

      await authApi.updateMe(updateData);
      dispatch(fetchUserStats());
      setSuccess('个人资料已更新');
      setIsEditing(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致');
      return;
    }

    if (newPassword.length < 6) {
      setError('密码至少需要 6 个字符');
      return;
    }

    setIsLoading(true);

    try {
      const data: PasswordChangeRequest = {
        old_password: oldPassword,
        new_password: newPassword,
      };
      await authApi.changePassword(data);
      setSuccess('密码已更新');
      setIsChangingPassword(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
  };

  if (!user) return <div className="club-table-loading"><span className="club-spinner" /><p>正在读取账户…</p></div>;
  return <div className="club-page"><ClubHeader><Link className="club-text-link" to="/"><Icon name="back" />返回大厅</Link><button className="club-icon-btn" onClick={handleLogout} aria-label="退出登录"><Icon name="logout" /></button></ClubHeader><main className="club-profile"><div className="club-profile-intro"><span className="club-avatar">{user.username.slice(0,1)}</span><div><span className="club-eyebrow">YOUR CORNER OF THE CLUB</span><h1>{user.username} 的牌桌空间</h1><p>管理账户，按自己的习惯享受对局。</p></div></div>
    {error && <div className="club-alert" role="alert">{error}</div>}{success && <div className="club-alert club-success" role="status">{success}</div>}
    <div className="club-profile-grid"><section className="club-profile-section"><div className="club-section-head"><h2>个人资料</h2>{!isEditing && <button className="club-text-button" onClick={() => setIsEditing(true)}>编辑资料</button>}</div>{isEditing ? <form className="club-form" onSubmit={handleUpdateProfile}><label>用户名<input autoComplete="username" required minLength={3} maxLength={50} value={editUsername} onChange={e => setEditUsername(e.target.value)} /></label><label>邮箱<input type="email" autoComplete="email" required value={editEmail} onChange={e => setEditEmail(e.target.value)} /></label><div className="club-form-buttons"><button className="club-btn club-btn-gold" disabled={isLoading}>{isLoading ? '保存中…' : '保存修改'}</button><button className="club-btn club-btn-outline" type="button" onClick={() => setIsEditing(false)}>取消</button></div></form> : <dl className="club-details"><div><dt>用户名</dt><dd>{user.username}</dd></div><div><dt>邮箱</dt><dd>{user.email}</dd></div><div><dt>加入时间</dt><dd>{new Date(user.created_at).toLocaleDateString('zh-CN')}</dd></div><div><dt>账户身份</dt><dd>{user.role === 'user' ? '俱乐部成员' : user.role === 'admin' ? '管理员' : '超级管理员'}{user.role !== 'user' && <Link className="club-text-button" to="/admin">进入管理后台</Link>}</dd></div></dl>}</section>
    <section className="club-profile-section"><div className="club-section-head"><h2>牌桌偏好</h2><Icon name="settings" /></div><PreferencesPanel /></section>
    <section className="club-profile-section"><div className="club-section-head"><h2>账户安全</h2></div>{isChangingPassword ? <form className="club-form" onSubmit={handleChangePassword}><label>当前密码<input type="password" autoComplete="current-password" required value={oldPassword} onChange={e => setOldPassword(e.target.value)} /></label><label>新密码<input type="password" autoComplete="new-password" required minLength={6} maxLength={100} value={newPassword} onChange={e => setNewPassword(e.target.value)} /></label><label>确认新密码<input type="password" autoComplete="new-password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} /></label><div className="club-form-buttons"><button className="club-btn club-btn-gold" disabled={isLoading}>{isLoading ? '保存中…' : '更新密码'}</button><button className="club-btn club-btn-outline" type="button" onClick={() => setIsChangingPassword(false)}>取消</button></div></form> : <><p className="club-section-description">使用独立的密码，保护你的俱乐部账户。</p><button className="club-btn club-btn-outline" onClick={() => setIsChangingPassword(true)}>修改密码<Icon name="arrow" /></button></>}</section>
    <section className="club-profile-section"><div className="club-section-head"><h2>对局统计</h2><span className="club-badge">已记录数据</span></div>{stats && stats.total_hands > 0 ? <div className="club-stats-grid">{[{ label:'累计牌局',value:chips(stats.total_games) },{label:'累计手数',value:chips(stats.total_hands)},{label:'胜率',value:`${(stats.win_rate*100).toFixed(1)}%`},{label:'最大赢得底池',value:chips(stats.biggest_pot_won)}].map(item => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}</div> : <div className="club-empty"><Icon name="cards" size={28} /><h3>你的故事，刚刚开始。</h3><p>目前没有可展示的已记录对局统计。</p><Link className="club-text-link" to="/">前往大厅<Icon name="arrow" /></Link></div>}</section></div></main></div>;
};
export default ProfilePage;
