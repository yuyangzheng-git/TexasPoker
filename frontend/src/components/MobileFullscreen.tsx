import React, { useEffect, useCallback, useState } from "react";

interface MobileFullscreenProps {
  children: React.ReactNode;
}

export const MobileFullscreen: React.FC<MobileFullscreenProps> = ({ children }) => {
  const [, setIsFullscreen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    // 检测是否为移动设备
    const checkMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );
    setIsMobile(checkMobile);

    // 移动端显示全屏提示
    if (checkMobile && !document.fullscreenElement) {
      setShowPrompt(true);
    }

    // 监听全屏变化
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      if (document.fullscreenElement) {
        setShowPrompt(false);
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
    };
  }, []);

  const enterFullscreen = useCallback(async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen();
      } else if ((elem as any).webkitRequestFullscreen) {
        await (elem as any).webkitRequestFullscreen();
      } else if ((elem as any).msRequestFullscreen) {
        await (elem as any).msRequestFullscreen();
      }

      // 尝试锁定横屏
      if (window.screen.orientation && (window.screen.orientation as any).lock) {
        try {
          await (window.screen.orientation as any).lock("landscape");
        } catch (e) {
          // 忽略锁定失败
        }
      }

      setShowPrompt(false);
    } catch (e) {
      console.log("Fullscreen not supported");
      setShowPrompt(false);
    }
  }, []);

  // 移动端全屏提示遮罩
  if (isMobile && showPrompt) {
    return (
      <div
        className="fixed inset-0 bg-gray-950 z-[99999] flex flex-col items-center justify-center"
        onClick={enterFullscreen}
      >
        <div className="text-center p-8">
          <div className="text-6xl mb-6 animate-pulse">🎰</div>
          <h1 className="text-2xl font-bold text-cyan-400 mb-4">Poker LLM Agent</h1>
          <p className="text-gray-400 mb-8">点击屏幕进入全屏游戏</p>
          <button
            className="px-8 py-4 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-lg transition-all active:scale-95"
            onClick={enterFullscreen}
          >
            开始游戏
          </button>
          <p className="text-gray-500 text-sm mt-6">建议横屏游玩以获得最佳体验</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
