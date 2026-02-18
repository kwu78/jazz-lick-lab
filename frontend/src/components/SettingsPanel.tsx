import { useState, useRef, useCallback } from "react";
import Panel from "./Panel";
import Button from "./Button";
import { saveSettings, type JobSettings } from "../api/jobs";

interface Props {
  jobId: string;
  initialSettings: JobSettings;
  getCurrentTime: () => number;
  onSaved: (settings: JobSettings) => void;
}

function median(arr: number[]): number {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

function AutoBadge() {
  return (
    <span className="text-[10px] bg-ink/10 text-muted px-1.5 py-0.5 rounded">
      auto
    </span>
  );
}

export default function SettingsPanel({
  jobId,
  initialSettings,
  getCurrentTime,
  onSaved,
}: Props) {
  const [bpmInput, setBpmInput] = useState(
    initialSettings.bpm?.toString() ?? ""
  );
  const [offsetSec, setOffsetSec] = useState(initialSettings.offset_sec);
  const [timeSig, setTimeSig] = useState(
    initialSettings.time_signature ?? "4/4"
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  // Track which fields were auto-detected (had values at mount time)
  const [autoDetected] = useState({
    bpm: initialSettings.bpm != null,
    offset: initialSettings.offset_sec !== 0,
    timeSig: initialSettings.time_signature != null,
  });

  // Tap tempo state
  const tapsRef = useRef<number[]>([]);
  const [tappedBpm, setTappedBpm] = useState<number | null>(null);
  const [tapCount, setTapCount] = useState(0);

  const handleTap = useCallback(() => {
    const now = Date.now();
    const taps = tapsRef.current;

    // Reset if more than 2 seconds since last tap
    if (taps.length > 0 && now - taps[taps.length - 1] > 2000) {
      tapsRef.current = [];
    }

    tapsRef.current.push(now);
    const count = tapsRef.current.length;
    setTapCount(count);

    if (count >= 4) {
      const intervals: number[] = [];
      for (let i = 1; i < tapsRef.current.length; i++) {
        intervals.push(tapsRef.current[i] - tapsRef.current[i - 1]);
      }
      const med = median(intervals);
      setTappedBpm(Math.round(60000 / med));
    } else {
      setTappedBpm(null);
    }
  }, []);

  const applyTappedBpm = useCallback(() => {
    if (tappedBpm !== null) {
      setBpmInput(tappedBpm.toString());
    }
  }, [tappedBpm]);

  const handleSetPlayhead = useCallback(() => {
    setOffsetSec(getCurrentTime());
  }, [getCurrentTime]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const bpmVal = bpmInput.trim() ? parseFloat(bpmInput) : undefined;
      if (bpmVal !== undefined && (isNaN(bpmVal) || bpmVal <= 0)) {
        setError("BPM must be a positive number");
        setSaving(false);
        return;
      }
      const result = await saveSettings(jobId, {
        bpm: bpmVal ?? null,
        offset_sec: offsetSec,
        time_signature: timeSig,
      });
      onSaved(result);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }, [jobId, bpmInput, offsetSec, timeSig, onSaved]);

  return (
    <Panel title="Settings">
      <div className="space-y-4">
        {/* BPM row */}
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium w-16">BPM</label>
          <input
            type="number"
            min={1}
            step={1}
            value={bpmInput}
            onChange={(e) => setBpmInput(e.target.value)}
            placeholder="120"
            className="border border-border rounded px-3 py-1.5 text-sm bg-transparent text-ink w-24 focus:outline-none focus:border-ink"
          />
          {autoDetected.bpm && <AutoBadge />}
          <Button variant="secondary" onClick={handleTap}>
            Tap Tempo
          </Button>
          {tapCount > 0 && tapCount < 4 && (
            <span className="text-xs text-muted">{tapCount} taps...</span>
          )}
          {tappedBpm !== null && (
            <>
              <span className="text-xs text-muted">
                {tappedBpm} BPM ({tapCount} taps)
              </span>
              <Button variant="secondary" onClick={applyTappedBpm}>
                Apply
              </Button>
            </>
          )}
        </div>

        {/* Offset row */}
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium w-16">Offset</label>
          <span className="text-sm font-mono w-24">
            {offsetSec.toFixed(2)}s
          </span>
          {autoDetected.offset && <AutoBadge />}
          <Button variant="secondary" onClick={handleSetPlayhead}>
            Set to Playhead
          </Button>
          <Button variant="secondary" onClick={() => setOffsetSec(0)}>
            Zero
          </Button>
        </div>

        {/* Time signature row */}
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium w-16">Time Sig</label>
          <select
            value={timeSig}
            onChange={(e) => setTimeSig(e.target.value)}
            className="border border-border rounded px-3 py-1.5 text-sm bg-page text-ink"
          >
            <option value="4/4">4/4</option>
            <option value="3/4">3/4</option>
            <option value="6/8">6/8</option>
            <option value="5/4">5/4</option>
          </select>
          {autoDetected.timeSig && <AutoBadge />}
        </div>

        <p className="text-xs text-muted">
          Offset marks where bar 1, beat 1 starts. Play the audio, pause at the
          downbeat, then click &ldquo;Set to Playhead&rdquo;.
        </p>

        {error && <p className="text-sm text-red-700">{error}</p>}
        {saved && <p className="text-sm text-green-700">Settings saved</p>}

        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </Panel>
  );
}
