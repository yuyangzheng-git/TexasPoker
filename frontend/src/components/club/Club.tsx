import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../../config';

export type IconName = 'arrow' | 'back' | 'chevron' | 'check' | 'close' | 'settings' | 'sound' | 'muted' | 'history' | 'pause' | 'play' | 'expand' | 'cards';
const paths: Record<IconName, React.ReactNode> = {
  arrow: <><path d="M4 12h15M13 5l7 7-7 7" /></>, back: <><path d="M20 12H5m6-7-7 7 7 7" /></>,
  chevron: <path d="m6 9 6 6 6-6" />, check: <path d="m5 12 4 4L19 6" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  settings: <><path d="M4 7h16M4 17h16" /><circle cx="8" cy="7" r="3" /><circle cx="16" cy="17" r="3" /></>,
  sound: <><path d="m11 4-5 4H2v8h4l5 4V4ZM15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14" /></>,
  muted: <><path d="m11 4-5 4H2v8h4l5 4V4Zm5 5 6 6m0-6-6 6" /></>,
  history: <><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6m3-4v6l4 2" /></>,
  pause: <><path d="M8 5v14M16 5v14" /></>, play: <path d="m8 4 12 8-12 8V4Z" />,
  expand: <path d="M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5" />,
  cards: <><rect x="6" y="3" width="13" height="18" rx="2" /><path d="m10 12 3-4 3 4-3 4-3-4ZM3 6v13" /></>,
};
export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link to="/" className={`club-brand ${compact ? 'is-compact' : ''}`} aria-label="Texas Poker — back to lobby"><span className="club-brand-mark">♠</span><span>TEXAS<span className="club-brand-light"> POKER</span><small>THE POKER CLUB</small></span></Link>;
}
interface Preferences { localDemo: boolean | null; sound: boolean; motion: boolean; fourColor: boolean; setSound: (v: boolean) => void; setMotion: (v: boolean) => void; setFourColor: (v: boolean) => void }
const ClubContext = createContext<Preferences>({ localDemo: null, sound: true, motion: true, fourColor: false, setSound: () => {}, setMotion: () => {}, setFourColor: () => {} });
const preference = (key: string, fallback: boolean) => { try { const value = localStorage.getItem(key); return value === null ? fallback : value === 'true'; } catch { return fallback; } };
export function ClubProvider({ children }: { children: React.ReactNode }) {
  const [localDemo, setLocalDemo] = useState<boolean | null>(null);
  const [sound, changeSound] = useState(() => preference('poker_sound', false));
  const [motion, changeMotion] = useState(() => preference('poker_motion', true));
  const [fourColor, changeFourColor] = useState(() => preference('poker_four_color', false));
  useEffect(() => { const controller = new AbortController(); fetch(`${API_BASE_URL}/api/local-mode`, { signal: controller.signal }).then(r => r.ok ? r.json() : null).then(data => setLocalDemo(['strategy', 'local-algorithm-demo'].includes(data?.mode))).catch(() => {}); return () => controller.abort(); }, []);
  useEffect(() => { document.documentElement.dataset.motion = String(motion); document.documentElement.dataset.fourColor = String(fourColor); }, [motion, fourColor]);
  const save = (key: string, value: boolean, update: (v: boolean) => void) => { localStorage.setItem(key, String(value)); update(value); };
  return <ClubContext.Provider value={{ localDemo, sound, motion, fourColor, setSound: v => save('poker_sound', v, changeSound), setMotion: v => save('poker_motion', v, changeMotion), setFourColor: v => save('poker_four_color', v, changeFourColor) }}>{children}</ClubContext.Provider>;
}
export const useClub = () => useContext(ClubContext);
export function ModeBadge() { const { localDemo } = useClub(); return <span className="club-mode"><span />{localDemo ? 'Strategy AI' : 'AI table'}</span>; }
export function ClubHeader({ children }: { children?: React.ReactNode }) { return <header className="club-header"><Brand /><nav className="club-header-actions">{children}</nav></header>; }
export function PreferencesPanel() {
  const { sound, motion, fourColor, setSound, setMotion, setFourColor } = useClub();
  return <div className="club-preferences">{[{ label: 'Sound effects', zh: '游戏音效', desc: 'Subtle cues, off by default', value: sound, set: setSound }, { label: 'Motion', zh: '界面动效', desc: 'Dealing and screen transitions', value: motion, set: setMotion }, { label: 'Four-color deck', zh: '四色牌面', desc: 'Color helps tell the suits apart', value: fourColor, set: setFourColor }].map(item => <label key={item.label} className="club-preference"><span><strong>{item.label}<Zh inline>{item.zh}</Zh></strong><small>{item.desc}</small></span><input type="checkbox" className="club-switch" checked={item.value} onChange={e => item.set(e.target.checked)} /></label>)}</div>;
}
export const chips = (n: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n || 0);
export const phaseName: Record<string, string> = { pre_flop: 'Pre-flop', flop: 'Flop', turn: 'Turn', river: 'River', showdown: 'Showdown', ended: 'Hand over' };
export const phaseNameZh: Record<string, string> = { pre_flop: '翻牌前', flop: '翻牌', turn: '转牌', river: '河牌', showdown: '摊牌', ended: '本手结束' };
// The server names hand ranks in Chinese; show the English name first.
export const handRankName: Record<string, string> = { 皇家同花顺: 'Royal Flush', 同花顺: 'Straight Flush', 四条: 'Four of a Kind', 葫芦: 'Full House', 同花: 'Flush', 顺子: 'Straight', 三条: 'Three of a Kind', 两对: 'Two Pair', 一对: 'One Pair', 高牌: 'High Card' };

// Secondary Chinese label shown under (or, inline, beside) the English text.
export function Zh({ children, inline = false }: { children: React.ReactNode; inline?: boolean }) {
  return <span className={`club-zh ${inline ? 'is-inline' : ''}`} lang="zh-CN">{children}</span>;
}

export function ClubDialog({ title, titleZh, children, onClose }: { title: string; titleZh?: string; children: React.ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className="club-dialog club-native-dialog" aria-label={title} onCancel={e => { e.preventDefault(); onClose(); }}><div className="club-section-head"><h2>{title}{titleZh && <Zh>{titleZh}</Zh>}</h2><button className="club-icon-btn" aria-label="Close" onClick={onClose}><Icon name="close" /></button></div>{children}</dialog>;
}
