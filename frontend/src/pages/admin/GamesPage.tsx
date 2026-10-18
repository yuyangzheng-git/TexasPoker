/**
 * Games Page - Game session management and statistics
 */
import React, { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { GameSession, User } from '../../types/auth';

const GamesPage: React.FC = () => {
  const [games, setGames] = useState<GameSession[]>([]);
  const [totalGames, setTotalGames] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [resultFilter, setResultFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<{
    game: GameSession;
    hands: Array<{
      hand_number: number;
      pot_size: number;
      player_result: string | null;
      chips_change: number;
      final_hand_rank: string | null;
    }>;
    user: User | null;
  } | null>(null);

  useEffect(() => {
    loadGames();
  }, [page, resultFilter]);

  const loadGames = async () => {
    try {
      setIsLoading(true);
      const params: { page: number; page_size: number; result?: string } = {
        page,
        page_size: 20,
      };
      if (resultFilter) params.result = resultFilter;

      const data = await adminApi.listGames(params);
      setGames(data.games);
      setTotalGames(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewGame = async (gameId: string) => {
    try {
      const data = await adminApi.getGame(gameId);
      setSelectedGame(data);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const formatDuration = (start: string, end: string | null): string => {
    if (!end) return 'In progress';
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    const minutes = Math.round((endTime - startTime) / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">对局记录</h1>
        <p className="text-gray-400 mt-1">查看已记录的对局与结算信息</p>
      </div>

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
          <button onClick={() => setError(null)} className="float-right text-red-400 hover:text-red-300">
            &times;
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <select
            value={resultFilter}
            onChange={(e) => { setResultFilter(e.target.value); setPage(1); }}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">全部结果</option>
            <option value="win">获胜</option>
            <option value="loss">失利</option>
            <option value="draw">平局</option>
          </select>
          <div className="text-gray-400 flex items-center">
            Total: {totalGames} games
          </div>
        </div>
      </div>

      {/* Games Table */}
      <div className="bg-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-700/50">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">牌局编号</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">玩家</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">开始时间</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">时长</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">手数</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">筹码净变化</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">结果</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">AI 对手</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((game) => {
                    const stackChange = game.ending_stack
                      ? game.ending_stack - game.starting_stack
                      : null;
                    return (
                      <tr key={game.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                        <td className="py-3 px-4 text-white font-mono text-sm">
                          {game.game_id}
                        </td>
                        <td className="py-3 px-4 text-gray-300">
                          {game.user_id ? `User #${game.user_id}` : 'Guest'}
                        </td>
                        <td className="py-3 px-4 text-gray-400 text-sm">
                          {new Date(game.started_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-gray-400 text-sm">
                          {formatDuration(game.started_at, game.ended_at)}
                        </td>
                        <td className="py-3 px-4 text-white">{game.total_hands}</td>
                        <td className="py-3 px-4">
                          {stackChange !== null ? (
                            <span
                              className={
                                stackChange > 0
                                  ? 'text-green-400'
                                  : stackChange < 0
                                  ? 'text-red-400'
                                  : 'text-gray-400'
                              }
                            >
                              {stackChange > 0 ? '+' : ''}
                              {stackChange.toLocaleString()}
                            </span>
                          ) : (
                            <span className="text-gray-500">-</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {game.result ? (
                            <span
                              className={`inline-block px-2 py-1 rounded text-xs ${
                                game.result === 'win'
                                  ? 'bg-green-500/20 text-green-400'
                                  : game.result === 'loss'
                                  ? 'bg-red-500/20 text-red-400'
                                  : 'bg-gray-500/20 text-gray-400'
                              }`}
                            >
                              {game.result}
                            </span>
                          ) : (
                            <span className="text-yellow-400 text-xs">进行中</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-400 text-sm">
                          {game.ai_opponents.length > 0
                            ? game.ai_opponents.slice(0, 3).join(', ') +
                              (game.ai_opponents.length > 3
                                ? ` +${game.ai_opponents.length - 3}`
                                : '')
                            : '-'}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleViewGame(game.game_id)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            查看详情
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="p-4 border-t border-gray-700 flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                Showing {games.length} of {totalGames} games
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition-colors"
                >
                  上一页
                </button>
                <span className="px-3 py-1 text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition-colors"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Game Detail Modal */}
      {selectedGame && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-3xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">
                Game Details: {selectedGame.game.game_id}
              </h3>
              <button
                onClick={() => setSelectedGame(null)}
                className="text-gray-400 hover:text-white text-xl"
              >
                &times;
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-gray-400 text-sm">玩家</p>
                <p className="text-white">
                  {selectedGame.user
                    ? selectedGame.user.username
                    : 'Guest'}
                </p>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-gray-400 text-sm">累计手数</p>
                <p className="text-white">{selectedGame.game.total_hands}</p>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-gray-400 text-sm">Starting Stack</p>
                <p className="text-white">{selectedGame.game.starting_stack.toLocaleString()}</p>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-gray-400 text-sm">Ending Stack</p>
                <p className="text-white">
                  {selectedGame.game.ending_stack?.toLocaleString() || '-'}
                </p>
              </div>
            </div>

            <h4 className="text-lg font-bold text-white mb-3">手牌记录</h4>
            {selectedGame.hands.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-700/50">
                      <th className="text-left py-2 px-3 text-gray-400 text-sm">Hand #</th>
                      <th className="text-left py-2 px-3 text-gray-400 text-sm">Pot Size</th>
                      <th className="text-left py-2 px-3 text-gray-400 text-sm">结果</th>
                      <th className="text-left py-2 px-3 text-gray-400 text-sm">Chips +/-</th>
                      <th className="text-left py-2 px-3 text-gray-400 text-sm">Final Hand</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedGame.hands.map((hand) => (
                      <tr key={hand.hand_number} className="border-t border-gray-700">
                        <td className="py-2 px-3 text-white">{hand.hand_number}</td>
                        <td className="py-2 px-3 text-white">{hand.pot_size.toLocaleString()}</td>
                        <td className="py-2 px-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs ${
                              hand.player_result === 'won'
                                ? 'bg-green-500/20 text-green-400'
                                : hand.player_result === 'lost'
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-gray-500/20 text-gray-400'
                            }`}
                          >
                            {hand.player_result || '-'}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={
                              hand.chips_change > 0
                                ? 'text-green-400'
                                : hand.chips_change < 0
                                ? 'text-red-400'
                                : 'text-gray-400'
                            }
                          >
                            {hand.chips_change > 0 ? '+' : ''}
                            {hand.chips_change.toLocaleString()}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-gray-300 text-sm">
                          {hand.final_hand_rank || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400">No hand records available</p>
            )}

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedGame(null)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GamesPage;
