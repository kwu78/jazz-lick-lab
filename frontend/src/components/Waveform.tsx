import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin, { type Region } from "wavesurfer.js/dist/plugins/regions.js";
import Button from "./Button";

interface Props {
  audioUrl: string;
  onRegionChange?: (start: number, end: number) => void;
}

export interface WaveformHandle {
  playRegion: (start: number, end: number) => void;
}

const Waveform = forwardRef<WaveformHandle, Props>(function Waveform(
  { audioUrl, onRegionChange },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionsRef = useRef<RegionsPlugin | null>(null);
  const activeRegionRef = useRef<Region | null>(null);
  const [playing, setPlaying] = useState(false);
  const [ready, setReady] = useState(false);
  const [regionTimes, setRegionTimes] = useState<{
    start: number;
    end: number;
  } | null>(null);

  const emitRegion = useCallback(
    (start: number, end: number) => {
      setRegionTimes({ start, end });
      onRegionChange?.(start, end);
    },
    [onRegionChange]
  );

  useImperativeHandle(ref, () => ({
    playRegion(start: number, end: number) {
      const ws = wsRef.current;
      if (!ws) return;
      ws.setTime(start);
      ws.play();
      // Stop at end
      const onTime = () => {
        if (ws.getCurrentTime() >= end) {
          ws.pause();
          ws.un("timeupdate", onTime);
        }
      };
      ws.on("timeupdate", onTime);
    },
  }));

  useEffect(() => {
    if (!containerRef.current) return;

    const regions = RegionsPlugin.create();
    regionsRef.current = regions;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#999",
      progressColor: "#333",
      cursorColor: "#111",
      height: 96,
      barWidth: 2,
      barGap: 1,
      url: audioUrl,
      plugins: [regions],
    });

    wsRef.current = ws;

    ws.on("ready", () => {
      setReady(true);
      const dur = ws.getDuration();
      const r = regions.addRegion({
        start: dur * 0.2,
        end: dur * 0.4,
        color: "rgba(17,17,17,0.12)",
        drag: true,
        resize: true,
      });
      activeRegionRef.current = r;
      emitRegion(r.start, r.end);
    });

    ws.on("play", () => setPlaying(true));
    ws.on("pause", () => setPlaying(false));

    regions.on("region-updated", (region: Region) => {
      emitRegion(region.start, region.end);
    });

    return () => {
      ws.destroy();
    };
  }, [audioUrl, emitRegion]);

  return (
    <div>
      <div
        ref={containerRef}
        className="border border-border rounded mb-3"
      />
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          disabled={!ready}
          onClick={() => wsRef.current?.playPause()}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        {regionTimes && (
          <span className="text-sm text-muted">
            Region: {regionTimes.start.toFixed(2)}s &ndash;{" "}
            {regionTimes.end.toFixed(2)}s
          </span>
        )}
      </div>
    </div>
  );
});

export default Waveform;
