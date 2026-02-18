import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useParams } from "react-router-dom";
import PageShell from "../components/PageShell";
import Panel from "../components/Panel";
import ErrorBox from "../components/ErrorBox";
import Waveform, { type WaveformHandle } from "../components/Waveform";
import ScoreViewer from "../components/ScoreViewer";
import SettingsPanel from "../components/SettingsPanel";
import SelectionPanel from "../components/SelectionPanel";
import AnalysisPanel from "../components/AnalysisPanel";
import CoachingPanel from "../components/CoachingPanel";
import PracticePackPanel from "../components/PracticePackPanel";
import Button from "../components/Button";
import {
  getJob,
  getAudioUrl,
  type Job,
  type Selection,
  type JobSettings,
} from "../api/jobs";
import { BASE_URL } from "../api/client";

const ALL_KEYS = [
  "C", "Db", "D", "Eb", "E", "F",
  "F#", "G", "Ab", "A", "Bb", "B",
];

const DEFAULT_SETTINGS: JobSettings = {
  bpm: null,
  offset_sec: 0,
  time_signature: "4/4",
};

export default function JobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [regionStart, setRegionStart] = useState<number | null>(null);
  const [regionEnd, setRegionEnd] = useState<number | null>(null);
  const [activeSelection, setActiveSelection] = useState<Selection | null>(
    null
  );
  const [previewKey, setPreviewKey] = useState("C");
  const waveformRef = useRef<WaveformHandle>(null);

  // Settings state
  const [settings, setSettings] = useState<JobSettings>(DEFAULT_SETTINGS);
  const [settingsVersion, setSettingsVersion] = useState(0);

  // Poll job status
  useEffect(() => {
    if (!jobId) return;
    let active = true;

    async function poll() {
      while (active) {
        try {
          const j = await getJob(jobId!);
          if (!active) break;
          setJob(j);
          // Initialize settings from job response
          if (j.status === "READY") {
            const s = (j as Record<string, unknown>).settings as JobSettings | null;
            if (s) {
              setSettings({
                bpm: s.bpm ?? null,
                offset_sec: s.offset_sec ?? 0,
                time_signature: s.time_signature ?? "4/4",
              });
            }
          }
          if (j.status === "READY" || j.status === "FAILED") break;
        } catch (err) {
          if (!active) break;
          setError(err instanceof Error ? err.message : "Failed to load job");
          break;
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
    }

    poll();
    return () => {
      active = false;
    };
  }, [jobId]);

  const handleRegionChange = useCallback((start: number, end: number) => {
    setRegionStart(start);
    setRegionEnd(end);
  }, []);

  const handlePlaySelection = useCallback(() => {
    if (regionStart != null && regionEnd != null && waveformRef.current) {
      waveformRef.current.playRegion(regionStart, regionEnd);
    }
  }, [regionStart, regionEnd]);

  const handleSettingsSaved = useCallback((saved: JobSettings) => {
    setSettings(saved);
    setSettingsVersion((v) => v + 1);
  }, []);

  const getWaveformTime = useCallback(
    () => waveformRef.current?.getCurrentTime() ?? 0,
    []
  );

  // Debounced score preview URL — only update after region stops changing
  const [debouncedRegion, setDebouncedRegion] = useState<{
    start: number;
    end: number;
  } | null>(null);

  useEffect(() => {
    if (regionStart == null || regionEnd == null) {
      setDebouncedRegion(null);
      return;
    }
    const timer = setTimeout(() => {
      setDebouncedRegion({ start: regionStart, end: regionEnd });
    }, 400);
    return () => clearTimeout(timer);
  }, [regionStart, regionEnd]);

  const scorePreviewUrl = useMemo(() => {
    if (!debouncedRegion || !jobId) return null;
    const params = new URLSearchParams({
      start_sec: debouncedRegion.start.toFixed(2),
      end_sec: debouncedRegion.end.toFixed(2),
      key: previewKey,
    });
    // settingsVersion forces refetch when settings change
    if (settingsVersion > 0) {
      params.set("_v", settingsVersion.toString());
    }
    return `${BASE_URL}/jobs/${jobId}/score-preview?${params}`;
  }, [debouncedRegion, previewKey, jobId, settingsVersion]);

  if (!jobId) return null;

  const isReady = job?.status === "READY";
  const statusLabel: Record<string, string> = {
    CREATED: "Queued",
    TRANSCRIBING: "Transcribing...",
    READY: "Ready",
    FAILED: "Failed",
  };
  const hasRegion = regionStart != null && regionEnd != null;

  // Parse beats per measure from time signature
  const beatsPerMeasure = settings.time_signature
    ? parseInt(settings.time_signature.split("/")[0], 10) || 4
    : 4;

  return (
    <PageShell>
      {error && <ErrorBox message={error} />}

      {/* Status */}
      {job && !isReady && (
        <Panel>
          <div className="flex items-center gap-3">
            <span className="font-serif text-lg">
              {statusLabel[job.status] ?? job.status}
            </span>
            {!isReady && job.status !== "FAILED" && (
              <span className="inline-block h-3 w-3 rounded-full bg-ink/30 animate-pulse" />
            )}
          </div>
          {job.error && (
            <p className="text-sm text-red-700 mt-2">{job.error}</p>
          )}
        </Panel>
      )}

      {/* Main content when ready */}
      {isReady && (
        <>
          <Panel title="Waveform">
            <Waveform
              ref={waveformRef}
              audioUrl={getAudioUrl(jobId)}
              onRegionChange={handleRegionChange}
              bpm={settings.bpm ?? undefined}
              offsetSec={settings.offset_sec}
              beatsPerMeasure={beatsPerMeasure}
            />
            <div className="mt-3 flex items-center gap-3">
              <Button
                variant="secondary"
                disabled={!hasRegion}
                onClick={handlePlaySelection}
              >
                Play Selection
              </Button>
              {!hasRegion && (
                <span className="text-xs text-muted">
                  Drag a region on the waveform first
                </span>
              )}
            </div>
          </Panel>

          <SettingsPanel
            jobId={jobId}
            initialSettings={settings}
            getCurrentTime={getWaveformTime}
            onSaved={handleSettingsSaved}
          />

          {/* Score Preview */}
          <Panel title="Score Preview">
            <div className="flex items-center gap-3 mb-4">
              <label className="flex items-center gap-1.5 text-xs text-muted">
                Key:
                <select
                  value={previewKey}
                  onChange={(e) => setPreviewKey(e.target.value)}
                  className="border border-border rounded px-2 py-1 text-xs bg-page text-ink"
                >
                  {ALL_KEYS.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </label>
              {hasRegion && (
                <span className="text-xs text-muted">
                  {regionStart!.toFixed(2)}s &ndash; {regionEnd!.toFixed(2)}s
                </span>
              )}
            </div>
            {scorePreviewUrl ? (
              <ScoreViewer musicXmlUrl={scorePreviewUrl} />
            ) : (
              <p className="text-sm text-muted py-4 text-center">
                Drag a region on the waveform to preview its score
              </p>
            )}
          </Panel>

          <SelectionPanel
            jobId={jobId}
            regionStart={regionStart}
            regionEnd={regionEnd}
            activeSelection={activeSelection}
            onSelect={setActiveSelection}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <AnalysisPanel
              jobId={jobId}
              selectionId={activeSelection?.selection_id ?? null}
            />
            <CoachingPanel
              jobId={jobId}
              selectionId={activeSelection?.selection_id ?? null}
            />
          </div>

          <PracticePackPanel
            jobId={jobId}
            selectionId={activeSelection?.selection_id ?? null}
          />
        </>
      )}
    </PageShell>
  );
}
