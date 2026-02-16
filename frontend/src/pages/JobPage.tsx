import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useParams } from "react-router-dom";
import PageShell from "../components/PageShell";
import Panel from "../components/Panel";
import ErrorBox from "../components/ErrorBox";
import Waveform, { type WaveformHandle } from "../components/Waveform";
import ScoreViewer from "../components/ScoreViewer";
import SelectionPanel from "../components/SelectionPanel";
import AnalysisPanel from "../components/AnalysisPanel";
import CoachingPanel from "../components/CoachingPanel";
import PracticePackPanel from "../components/PracticePackPanel";
import Button from "../components/Button";
import { getJob, getAudioUrl, type Job, type Selection } from "../api/jobs";
import { BASE_URL } from "../api/client";

const ALL_KEYS = [
  "C", "Db", "D", "Eb", "E", "F",
  "F#", "G", "Ab", "A", "Bb", "B",
];

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
    return `${BASE_URL}/jobs/${jobId}/score-preview?${params}`;
  }, [debouncedRegion, previewKey, jobId]);

  if (!jobId) return null;

  const isReady = job?.status === "READY";
  const statusLabel: Record<string, string> = {
    CREATED: "Queued",
    TRANSCRIBING: "Transcribing...",
    READY: "Ready",
    FAILED: "Failed",
  };
  const hasRegion = regionStart != null && regionEnd != null;

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
