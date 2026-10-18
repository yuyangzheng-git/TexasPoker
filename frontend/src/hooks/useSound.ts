import { useCallback, useRef } from "react";

type SoundType = "deal" | "bet" | "fold" | "check" | "win" | "lose" | "tick";

interface SoundConfig {
  frequency: number;
  duration: number;
  volume: number;
  type: "sine" | "square" | "triangle" | "sawtooth";
}

const SOUND_CONFIGS: Record<SoundType, SoundConfig> = {
  deal: { frequency: 800, duration: 0.15, volume: 0.3, type: "sine" },
  bet: { frequency: 600, duration: 0.2, volume: 0.3, type: "square" },
  fold: { frequency: 400, duration: 0.25, volume: 0.25, type: "sine" },
  check: { frequency: 500, duration: 0.1, volume: 0.2, type: "sine" },
  win: { frequency: 800, duration: 0.3, volume: 0.35, type: "sine" },
  lose: { frequency: 300, duration: 0.3, volume: 0.25, type: "sine" },
  tick: { frequency: 1000, duration: 0.05, volume: 0.15, type: "sine" },
};

export const useSound = () => {
  const audioContextRef = useRef<AudioContext | null>(null);

  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  const playSound = useCallback(
    (soundType: SoundType) => {
      if (localStorage.getItem('poker_sound') !== 'true') return;
      try {
        const ctx = getAudioContext();
        const config = SOUND_CONFIGS[soundType];

        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.type = config.type;
        oscillator.frequency.value = config.frequency;

        gainNode.gain.setValueAtTime(config.volume * 0.25, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + config.duration);

        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + config.duration);
      } catch (e) {
        console.error("Failed to play sound:", e);
      }
    },
    [getAudioContext]
  );

  return { playSound };
};
