import { useMemo } from "react";

export interface PianoRollNote {
  pitch_midi: number;
  start_sec: number;
  duration_sec: number;
}

interface Props {
  notes: PianoRollNote[];
  startSec: number;
  endSec: number;
  currentTimeSec?: number;
}

const NOTE_HEIGHT = 6;
const PITCH_PAD = 2; // extra semitones above/below visible range
const PITCH_LABELS = [
  "C", "Db", "D", "Eb", "E", "F",
  "F#", "G", "Ab", "A", "Bb", "B",
];

function midiLabel(midi: number): string {
  return `${PITCH_LABELS[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export default function PianoRoll({
  notes,
  startSec,
  endSec,
  currentTimeSec,
}: Props) {
  const span = endSec - startSec;

  // Filter to notes overlapping visible window
  const visible = useMemo(
    () =>
      notes.filter(
        (n) => n.start_sec + n.duration_sec > startSec && n.start_sec < endSec
      ),
    [notes, startSec, endSec]
  );

  // Pitch range
  const { minPitch, maxPitch } = useMemo(() => {
    if (visible.length === 0) return { minPitch: 48, maxPitch: 84 };
    let lo = Infinity;
    let hi = -Infinity;
    for (const n of visible) {
      if (n.pitch_midi < lo) lo = n.pitch_midi;
      if (n.pitch_midi > hi) hi = n.pitch_midi;
    }
    return {
      minPitch: lo - PITCH_PAD,
      maxPitch: hi + PITCH_PAD,
    };
  }, [visible]);

  const pitchRange = maxPitch - minPitch + 1;
  const totalHeight = pitchRange * NOTE_HEIGHT;

  // Playhead position
  const playheadPct =
    currentTimeSec != null &&
    currentTimeSec >= startSec &&
    currentTimeSec <= endSec
      ? ((currentTimeSec - startSec) / span) * 100
      : null;

  return (
    <div
      className="relative overflow-hidden border border-border rounded bg-white"
      style={{ height: Math.max(totalHeight + 32, 120) }}
    >
      {/* Pitch labels (left gutter) */}
      <div
        className="absolute left-0 top-0 bottom-0 z-10 border-r border-border bg-page"
        style={{ width: 40 }}
      >
        {Array.from({ length: pitchRange }, (_, i) => {
          const midi = maxPitch - i;
          const isC = midi % 12 === 0;
          return (
            <div
              key={midi}
              className="absolute right-1 text-right leading-none"
              style={{
                top: i * NOTE_HEIGHT + 16 - 4,
                fontSize: 8,
                color: isC ? "#111" : "#999",
              }}
            >
              {isC ? midiLabel(midi) : ""}
            </div>
          );
        })}
      </div>

      {/* Grid + notes area */}
      <div className="absolute top-0 bottom-0 right-0" style={{ left: 40 }}>
        {/* Horizontal pitch gridlines */}
        {Array.from({ length: pitchRange }, (_, i) => {
          const midi = maxPitch - i;
          const isC = midi % 12 === 0;
          return (
            <div
              key={midi}
              className="absolute left-0 right-0"
              style={{
                top: i * NOTE_HEIGHT + 16,
                height: 1,
                backgroundColor: isC
                  ? "rgba(17,17,17,0.2)"
                  : "rgba(17,17,17,0.06)",
              }}
            />
          );
        })}

        {/* Note rectangles */}
        {visible.map((n, i) => {
          const leftPct = Math.max(
            0,
            ((n.start_sec - startSec) / span) * 100
          );
          const rightEdge = Math.min(endSec, n.start_sec + n.duration_sec);
          const widthPct = ((rightEdge - Math.max(n.start_sec, startSec)) / span) * 100;
          const row = maxPitch - n.pitch_midi;
          return (
            <div
              key={i}
              className="absolute rounded-sm"
              style={{
                left: `${leftPct}%`,
                width: `${Math.max(widthPct, 0.3)}%`,
                top: row * NOTE_HEIGHT + 16,
                height: NOTE_HEIGHT - 1,
                backgroundColor: "#111",
              }}
            />
          );
        })}

        {/* Playhead */}
        {playheadPct != null && (
          <div
            className="absolute top-0 bottom-0 z-20"
            style={{
              left: `${playheadPct}%`,
              width: 2,
              backgroundColor: "rgba(220, 38, 38, 0.8)",
            }}
          />
        )}
      </div>
    </div>
  );
}
