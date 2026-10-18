import React, { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { Icon } from './club/Club';
interface GameInfoPanelProps { showThinking?: boolean; onClose?: () => void }
export const GameInfoPanel: React.FC<GameInfoPanelProps> = ({ showThinking = false, onClose }) => {
  const { chatHistory, gameState, agentThinking, gameResult } = useSelector((s: RootState) => s.game);
  const [tab, setTab] = useState(showThinking ? 'review' : 'history'); const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (showThinking) setTab('review'); }, [showThinking]);
  useEffect(() => { if (tab === 'history') end.current?.scrollIntoView({ block: 'nearest' }); }, [chatHistory, tab]);
  const names: Record<string, string> = { system: '牌桌', player_human: '你' };
  gameState?.players.forEach(p => { if (!p.isHuman) names[p.id] = p.name; });
  const thoughts = Object.entries(agentThinking).filter(([, value]) => value.thinking);
  return <aside className="club-game-info"><div className="club-info-header"><div><span className="club-eyebrow">AT THE TABLE</span><h2>牌桌手记</h2></div>{onClose && <button className="club-icon-btn" onClick={onClose} aria-label="关闭牌桌手记"><Icon name="close" /></button>}</div><div className="club-info-tabs" role="tablist" aria-label="牌桌信息"><button role="tab" id="history-tab" aria-controls="history-panel" aria-selected={tab === 'history'} onClick={() => setTab('history')}>行动记录</button><button role="tab" id="review-tab" aria-controls="review-panel" aria-selected={tab === 'review'} onClick={() => setTab('review')}>赛后复盘{gameResult && <i />}</button></div>
    {tab === 'history' ? <div className="club-info-scroll" role="tabpanel" id="history-panel" aria-labelledby="history-tab">{chatHistory.length ? chatHistory.map((message, index) => <div className={`club-log-item ${message.type === 'system' ? 'is-system' : ''}`} key={`${message.timestamp}-${index}`}>{message.type === 'system' ? <span>{message.message}</span> : <><div className="club-log-byline"><strong>{names[message.sender] || message.sender}</strong><time>{new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</time></div><p>{message.message.replace(/【([^】]+)】/, '$1 · ')}</p></>}</div>) : <div className="club-empty"><Icon name="history" size={28} /><h3>故事还未开始</h3><p>每一次下注与公开发言，<br />都会记录在这里。</p></div>}<div ref={end} /></div> : <div className="club-info-scroll" role="tabpanel" id="review-panel" aria-labelledby="review-tab">{!gameResult ? <div className="club-empty"><Icon name="cards" size={28} /><h3>让这手牌先打完</h3><p>为了公平对局，AI 思考内容<br />将在本手结束后公开。</p></div> : thoughts.length ? thoughts.map(([id, state]) => <details className="club-review-item" key={id} open><summary><span className="club-avatar avatar-small">{(names[id] || id).slice(0, 1)}</span><strong>{names[id] || id}</strong><Icon name="chevron" /></summary><p>{state.thinking}</p></details>) : <div className="club-empty"><h3>暂无决策思考记录</h3><p>你仍可在行动记录中回看本手过程。</p></div>}</div>}
  </aside>;
};
