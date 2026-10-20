import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { setPaused } from '../store/gameSlice';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSound } from '../hooks/useSound';
import { ActionType } from '../types/game';
import { PokerTable } from '../components/PokerTable';
import { GameInfoPanel } from '../components/GameInfoPanel';
import { ActionPanel } from '../components/ActionPanel';
import { GameResultOverlay } from '../components/GameResultOverlay';
import { Brand, Icon, ModeBadge, PreferencesPanel, ClubDialog, chips, phaseName, useClub } from '../components/club/Club';
import { Card } from '../components/Card';

export const GamePage: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>(); const navigate = useNavigate(); const dispatch = useDispatch<AppDispatch>();
  const { submitAction, sendMessage } = useWebSocket(gameId); const { playSound } = useSound(); const prefs = useClub();
  const { gameState: game, connected, connectionError, gameFinished, playerActionRequest: request, gameResult, currentActingPlayerId: acting, isPaused, actionSubmitting, actionError } = useSelector((s: RootState) => s.game);
  const [infoOpen, setInfoOpen] = useState(false); const [review, setReview] = useState(false); const [settings, setSettings] = useState(false);
  const mine = game?.players.find(p => p.isHuman); const actor = game?.players.find(p => p.id === acting);
  const lastPhase = useRef(''); const lastResult = useRef<typeof gameResult>();
  useEffect(() => { if (game?.phase && lastPhase.current && lastPhase.current !== game.phase) playSound('deal'); lastPhase.current = game?.phase || ''; }, [game?.phase, playSound]);
  useEffect(() => { if (gameResult && lastResult.current !== gameResult) { const change = gameResult.allocations.find(a => a.playerId === 'player_human')?.stackChange || 0; playSound(change > 0 ? 'win' : 'lose'); } lastResult.current = gameResult; }, [gameResult, playSound]);
  const act = useCallback((action: ActionType, amount?: number, speech?: string) => { if (!mine || !connected || actionSubmitting) return; playSound(action === ActionType.FOLD ? 'fold' : action === ActionType.CHECK ? 'check' : 'bet'); submitAction(mine.id, action, amount, speech); }, [mine, connected, actionSubmitting, playSound, submitAction]);
  const next = () => { if (gameFinished) navigate('/'); else sendMessage({ type: 'READY_FOR_NEXT_HAND' }); };
  const showReview = () => { setReview(true); setInfoOpen(true); };
  const myTurn = request.isHumanTurn && connected;
  useEffect(() => { const base = 'Texas Poker · 扑克俱乐部'; document.title = myTurn ? `● 轮到你 · ${base}` : base; return () => { document.title = base; }; }, [myTurn]);
  return <main className="club-game"><header className="club-game-header"><div className="club-game-brand"><Link to="/" className="club-icon-btn" aria-label="返回大厅"><Icon name="back" /></Link><Brand compact /></div><div className="club-game-session"><span className="club-badge">{game ? `${game.players.length} 人桌` : '准备中'}</span><ModeBadge /></div><div className="club-game-tools"><button className="club-icon-btn" aria-label={prefs.sound ? '关闭音效' : '开启音效'} aria-pressed={prefs.sound} onClick={() => prefs.setSound(!prefs.sound)}><Icon name={prefs.sound ? 'sound' : 'muted'} /></button><button className="club-icon-btn" aria-label={isPaused ? '继续对局' : '暂停对局'} aria-pressed={isPaused} disabled={!connected || gameFinished} title="当前行动完成后暂停；已有行动时限不变" onClick={() => { dispatch(setPaused(!isPaused)); sendMessage({ type: isPaused ? 'RESUME' : 'PAUSE' }); }}><Icon name={isPaused ? 'play' : 'pause'} /></button><button className="club-icon-btn" aria-label="游戏设置" onClick={() => setSettings(true)}><Icon name="settings" /></button><button className={`club-icon-btn ${infoOpen ? 'is-active' : ''}`} aria-label={infoOpen ? '关闭牌桌手记' : '打开牌桌手记'} aria-expanded={infoOpen} onClick={() => { setReview(false); setInfoOpen(!infoOpen); }}><Icon name="history" /></button></div></header>
    {connectionError && <div className="club-connection-alert" role="alert"><span>{connectionError}</span><Link to="/">返回大厅</Link></div>}
    <div className={`club-game-layout ${infoOpen ? 'with-info' : ''}`}><div className="club-game-main"><div className="club-game-status"><span><i className={connected ? 'is-online' : ''} />{connected ? isPaused ? '对局已暂停' : '牌桌已连接' : '正在连接牌桌…'}</span><span>{game ? phaseName[game.phase] : '等待发牌'}{actor && !gameResult && ` · ${actor.isHuman ? '轮到你' : `${actor.name} 正在思考`}`}</span></div><PokerTable />
    <div className="club-player-dock"><div className="club-your-hand"><span className="club-dock-label">你的手牌</span><div>{mine?.holeCards?.length ? mine.holeCards.map((c, i) => <Card key={i} rank={c.rank} suit={c.suit} />) : <><Card faceDown /><Card faceDown /></>}</div><span className="club-dock-stack">可用筹码 <strong>{chips(mine?.stack || 0)}</strong></span></div><div className="club-dock-content">{gameResult ? <GameResultOverlay visible finished={gameFinished} busted={gameFinished && (mine?.stack ?? 0) <= 0} allocations={gameResult.allocations} playerName={mine?.name || '你'} onContinue={next} onReview={showReview} disabled={!connected} /> : request.isHumanTurn && connected ? <ActionPanel isActive callAmount={request.callAmount} pot={request.pot || game?.pot || 0} myStack={mine?.stack || 0} timeLimit={request.timeLimit} validActions={request.validActions} minRaise={request.minRaise} maxRaise={request.maxRaise} requestId={request.requestId} submitting={actionSubmitting} error={actionError} onAction={act} /> : <div className="club-waiting"><span className="club-eyebrow">{isPaused ? 'A MOMENT TO BREATHE' : 'READ THE TABLE'}</span><h2>{isPaused ? '稍作休息，下一步由你决定。' : actor ? `${actor.name} 正在考虑下一步…` : game ? '静观牌局，等待你的回合。' : '正在为你准备牌桌。'}</h2><p>{isPaused ? '点击顶部继续按钮，恢复对局。' : mine?.status === 'folded' ? '你已弃牌，可以观察余下对局并在结束后查看复盘。' : '留意对手的行动，也留一点耐心给好牌。'}</p></div>}</div></div><footer className="club-game-footer"><span>模拟筹码 · 无现金交易</span><button onClick={() => { setReview(false); setInfoOpen(!infoOpen); }}>牌桌手记<Icon name="history" size={13} /></button></footer></div>
    {infoOpen && <><button className="club-info-scrim" aria-label="关闭侧栏" onClick={() => setInfoOpen(false)} /><GameInfoPanel showThinking={review} onClose={() => setInfoOpen(false)} /></>}</div>
    {settings && <ClubDialog title="牌桌偏好" onClose={() => setSettings(false)}><PreferencesPanel /><button className="club-btn club-btn-outline club-btn-wide" onClick={async () => { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen?.().catch(() => {}); }}><Icon name="expand" />切换全屏</button></ClubDialog>}
  </main>;
};
