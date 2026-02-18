import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef, useMemo } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin, { type Region } from "wavesurfer.js/dist/plugins/regions.js";
import Button from "./Button";

interface Props {
  audioUrl: string;
  onRegionChange?: (start: number, end: number) => void;
  bpm?: number;
  offsetSec?: number;
  beatsPerMeasure?: number;
}

export interface WaveformHandle {
  playRegion: (start: number, end: number) => void;
  getCurrentTime: () => number;
}

const Waveform = forwardRef<WaveformHandle, Props>(function Waveform(
  { audioUrl, onRegionChange, bpm, offsetSec = 0, beatsPerMeasure = 4 },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionsRef = useRef<RegionsPlugin | null>(null);
  const activeRegionRef = useRef<Region | null>(null);
  const [playing, setPlaying] = useState(false);
  const [ready, setReady] = useState(false);
  const [duration, setDuration] = useState(0);
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
      const onTime = () => {
        if (ws.getCurrentTime() >= end) {
          ws.pause();
          ws.un("timeupdate", onTime);
        }
      };
      ws.on("timeupdate", onTime);
    },
    getCurrentTime() {
      return wsRef.current?.getCurrentTime() ?? 0;
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
      setDuration(ws.getDuration());
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

  // Beat grid lines
  const beatLines = useMemo(() => {
    if (!bpm || bpm <= 0 || duration <= 0) return [];
    const beatSec = 60 / bpm;
    const lines: { pct: number; isMeasure: boolean }[] = [];
    let beatIndex = 0;
    let t = offsetSec;
    // Start from first beat at or after 0
    if (t < 0) {
      const skip = Math.ceil(-t / beatSec);
      t += skip * beatSec;
      beatIndex += skip;
    }
    while (t <= duration) {
      if (t >= 0) {
        lines.push({
          pct: (t / duration) * 100,
          isMeasure: beatIndex % beatsPerMeasure === 0,
        });
      }
      t += beatSec;
      beatIndex++;
    }
    return lines;
  }, [bpm, offsetSec, beatsPerMeasure, duration]);

  return (
    <div>
      <div className="relative">
        <div
          ref={containerRef}
          className="border border-border rounded mb-3"
        />
        {beatLines.length > 0 && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden mb-3">
            {beatLines.map((line, i) => (
              <div
                key={i}
                className="absolute top-0 bottom-0"
                style={{
                  left: `${line.pct}%`,
                  width: "1px",
                  backgroundColor: line.isMeasure
                    ? "rgba(17,17,17,0.4)"
                    : "rgba(17,17,17,0.15)",
                }}
              />
            ))}
          </div>
        )}
      </div>
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
