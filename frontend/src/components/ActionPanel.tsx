import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSound } from "../hooks/useSound";
import { ActionType } from "../types/game";

// 快捷放话短语
const QUICK_SPEECHES = [
  { label: "🔥", text: "我要加注！谁怕谁？" },
  { label: "🤔", text: "让我想想..." },
  { label: "😏", text: "你确定要跟吗？" },
  { label: "💪", text: "今天运气不错" },
  { label: "🎯", text: "这把我感觉很准" },
  { label: "😎", text: "来吧，我准备好了" },
  { label: "🃏", text: "有意思..." },
  { label: "💀", text: "你可能会后悔的" },
];

interface ActionPanelProps {
  isActive: boolean;
  callAmount: number;
  pot: number;
  myStack: number;
  timeLimit?: number;
  onAction: (action: ActionType, amount?: number, speech?: string) => void;
}

export const ActionPanel: React.FC<ActionPanelProps> = ({
  isActive,
  callAmount,
  pot,
  myStack,
  timeLimit = 30000,
  onAction,
}) => {
  const { playSound } = useSound();
  const [raiseAmount, setRaiseAmount] = useState(callAmount * 2 || 20);
  const [timeLeft, setTimeLeft] = useState(timeLimit / 1000);
  const [lastTickTime, setLastTickTime] = useState(0);
  const [speech, setSpeech] = useState("");
  const [showSpeechPanel, setShowSpeechPanel] = useState(false);

  useEffect(() => {
    if (!isActive) {
      setTimeLeft(timeLimit / 1000);
      setLastTickTime(0);
      setSpeech("");
      return;
    }
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        const newTime = prev - 1;
        // Play tick sound when time is low (last 10 seconds)
        if (newTime > 0 && newTime <= 10 && newTime !== lastTickTime) {
          playSound("tick");
          setLastTickTime(newTime);
        }
        if (newTime <= 0) {
          onAction(ActionType.FOLD);
          return 0;
        }
        return newTime;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [isActive, timeLimit, onAction, lastTickTime, playSound]);

  useEffect(() => {
    if (isActive) {
      const minRaise = callAmount > 0 ? callAmount * 2 : 20;
      setRaiseAmount(Math.max(minRaise, Math.min(pot / 2, myStack)));
    }
  }, [isActive, callAmount, pot, myStack]);

  const handleAction = (action: ActionType, amount?: number) => {
    onAction(action, amount, speech || undefined);
    setSpeech("");
  };

  const handleQuickSpeech = (text: string) => {
    setSpeech(text);
  };

  const minRaise = callAmount > 0 ? callAmount * 2 : 20;
  const timerPct = (timeLeft / (timeLimit / 1000)) * 100;

  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          className="fixed left-1/2 z-40"
          style={{ x: "-50%", bottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))" }}
          initial={{ opacity: 0, y: 60 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 60 }}
          transition={{ type: "spring", damping: 24, stiffness: 260 }}
        >
          <div className="bg-gray-900 border border-gray-600 rounded-2xl shadow-2xl overflow-hidden w-[520px]">
            {/* Timer bar */}
            <div className="h-1 bg-gray-800 w-full">
              <motion.div
                className={"h-full " + (timerPct > 50 ? "bg-green-500" : timerPct > 25 ? "bg-yellow-500" : "bg-red-500")}
                animate={{ width: timerPct + "%" }}
                transition={{ duration: 1, ease: "linear" }}
              />
            </div>

            <div className="px-5 py-4">
              {/* Timer display */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-cyan-400 font-mono text-xs font-bold tracking-widest">YOUR TURN</span>
                <span className={"font-mono text-xs " + (timeLeft > 10 ? "text-gray-400" : "text-red-400 animate-pulse")}>
                  {timeLeft}s
                </span>
              </div>

              {/* Speech section */}
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <button
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      showSpeechPanel
                        ? "bg-purple-600 text-white"
                        : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                    }`}
                    onClick={() => setShowSpeechPanel(!showSpeechPanel)}
                  >
                    💬 放话
                  </button>
                  {speech && (
                    <span className="text-xs text-purple-400 truncate flex-1">
                      "{speech}"
                    </span>
                  )}
                </div>

                <AnimatePresence>
                  {showSpeechPanel && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      {/* Quick speech buttons */}
                      <div className="flex flex-wrap gap-1 mb-2">
                        {QUICK_SPEECHES.map((item, i) => (
                          <button
                            key={i}
                            className={`text-xs px-2 py-1 rounded transition-colors ${
                              speech === item.text
                                ? "bg-purple-600 text-white"
                                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                            }`}
                            onClick={() => handleQuickSpeech(item.text)}
                            title={item.text}
                          >
                            {item.label}
                          </button>
                        ))}
                        {speech && (
                          <button
                            className="text-xs px-2 py-1 rounded bg-red-800 text-white hover:bg-red-700"
                            onClick={() => setSpeech("")}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      {/* Custom speech input */}
                      <input
                        type="text"
                        className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                        placeholder="输入自定义放话..."
                        value={speech}
                        onChange={e => setSpeech(e.target.value)}
                        maxLength={50}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Raise amount section */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-gray-400 mb-1 font-mono">
                  <span>RAISE AMOUNT</span>
                  <span className="text-yellow-400 font-bold">${raiseAmount.toFixed(0)}</span>
                </div>
                <input
                  type="range"
                  min={minRaise}
                  max={myStack}
                  value={raiseAmount}
                  onChange={e => setRaiseAmount(Number(e.target.value))}
                  className="w-full accent-yellow-400"
                />
                {/* Preset buttons */}
                <div className="flex gap-2 mt-2">
                  {[
                    { label: "Min", value: minRaise },
                    { label: "½ Pot", value: pot / 2 },
                    { label: "Pot", value: pot },
                    { label: "2x Pot", value: pot * 2 },
                  ].map(preset => (
                    <button
                      key={preset.label}
                      className="flex-1 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded font-mono transition-colors"
                      onClick={() => setRaiseAmount(Math.max(minRaise, Math.min(preset.value, myStack)))}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action buttons */}
              <div className="grid grid-cols-4 gap-2">
                <button
                  className="py-3 rounded-xl bg-red-800 hover:bg-red-700 text-white font-bold text-sm tracking-wide transition-all active:scale-95 border border-red-700"
                  onClick={() => handleAction(ActionType.FOLD)}
                >
                  FOLD
                </button>
                <button
                  className="py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-white font-bold text-sm tracking-wide transition-all active:scale-95 border border-gray-600"
                  onClick={() => handleAction(callAmount > 0 ? ActionType.CALL : ActionType.CHECK, callAmount)}
                >
                  {callAmount > 0 ? `CALL $${callAmount.toFixed(0)}` : "CHECK"}
                </button>
                <button
                  className="py-3 rounded-xl bg-blue-700 hover:bg-blue-600 text-white font-bold text-sm tracking-wide transition-all active:scale-95 border border-blue-600"
                  onClick={() => handleAction(ActionType.RAISE, raiseAmount)}
                >
                  RAISE ${raiseAmount.toFixed(0)}
                </button>
                <button
                  className="py-3 rounded-xl bg-yellow-500 hover:bg-yellow-400 text-black font-bold text-sm tracking-wide transition-all active:scale-95 border border-yellow-400"
                  onClick={() => handleAction(ActionType.ALLIN, myStack)}
                >
                  ALL-IN
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
