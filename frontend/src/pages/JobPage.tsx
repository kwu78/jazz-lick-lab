import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import PageShell from "../components/PageShell";
import Panel from "../components/Panel";
import ErrorBox from "../components/ErrorBox";
import Waveform from "../components/Waveform";
import SelectionPanel from "../components/SelectionPanel";
import AnalysisPanel from "../components/AnalysisPanel";
import CoachingPanel from "../components/CoachingPanel";
import PracticePackPanel from "../components/PracticePackPanel";
import { getJob, getAudioUrl, type Job, type Selection } from "../api/jobs";

export default function JobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [regionStart, setRegionStart] = useState<number | null>(null);
  const [regionEnd, setRegionEnd] = useState<number | null>(null);
  const [activeSelection, setActiveSelection] = useState<Selection | null>(
    null
  );

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

  if (!jobId) return null;

  const isReady = job?.status === "READY";
  const statusLabel: Record<string, string> = {
    CREATED: "Queued",
    TRANSCRIBING: "Transcribing...",
    READY: "Ready",
    FAILED: "Failed",
  };

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
              audioUrl={getAudioUrl(jobId)}
              onRegionChange={handleRegionChange}
            />
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
