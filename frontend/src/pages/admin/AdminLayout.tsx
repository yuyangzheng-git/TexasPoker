import React, { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { RootState } from '../../store';
import { Brand, Icon, IconName } from '../../components/club/Club';
const navigation: { path: string; label: string; icon: IconName }[] = [{path:'/admin',label:'概览',icon:'cards'},{path:'/admin/users',label:'成员管理',icon:'user'},{path:'/admin/games',label:'对局记录',icon:'history'},{path:'/admin/ai-agents',label:'AI 对手',icon:'cards'},{path:'/admin/settings',label:'系统设置',icon:'settings'}];
const AdminLayout: React.FC = () => {
  const { user } = useSelector((s: RootState) => s.auth); const location = useLocation(); const [open, setOpen] = useState(false);
  if (!user || user.role === 'user') return null;
  return <div className="club-admin"><header className="club-admin-mobile"><Brand compact /><button className="club-icon-btn" aria-label={open ? '关闭管理导航' : '打开管理导航'} aria-expanded={open} onClick={() => setOpen(!open)}><Icon name={open ? 'close' : 'settings'} /></button></header>{open && <button className="club-admin-scrim" aria-label="关闭导航" onClick={() => setOpen(false)} />}<aside className={`club-admin-sidebar ${open ? 'is-open' : ''}`}><Brand /><span className="club-eyebrow">CLUB MANAGEMENT</span><nav aria-label="管理后台">{navigation.map(item => <Link key={item.path} to={item.path} className={(item.path === '/admin' ? location.pathname === item.path : location.pathname.startsWith(item.path)) ? 'is-active' : ''} onClick={() => setOpen(false)}><Icon name={item.icon} />{item.label}</Link>)}</nav><div className="club-admin-account"><span className="club-avatar">{user.username.slice(0,1)}</span><div><strong>{user.username}</strong><small>{user.role === 'super_admin' ? '超级管理员' : '管理员'}</small></div></div><div className="club-admin-links"><Link to="/profile">个人中心</Link><Link to="/">返回大厅<Icon name="arrow" size={14} /></Link></div></aside><main className="club-admin-content club-legacy"><Outlet /></main></div>;
};
export default AdminLayout;
