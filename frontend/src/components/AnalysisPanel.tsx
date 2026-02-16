import { useState, useEffect } from "react";
import Panel from "./Panel";
import ErrorBox from "./ErrorBox";
import { getAnalysis, type Analysis } from "../api/jobs";

interface Props {
  jobId: string;
  selectionId: string | null;
}

export default function AnalysisPanel({ jobId, selectionId }: Props) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selectionId) {
      setAnalysis(null);
      return;
    }
    setLoading(true);
    setError("");
    getAnalysis(jobId, selectionId)
      .then(setAnalysis)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed"))
      .finally(() => setLoading(false));
  }, [jobId, selectionId]);

  if (!selectionId) {
    return (
      <Panel title="Analysis">
        <p className="text-sm text-muted">Select a region to analyze.</p>
      </Panel>
    );
  }

  return (
    <Panel title="Analysis">
      {error && <ErrorBox message={error} />}
      {loading && <p className="text-sm text-muted">Loading...</p>}
      {analysis && (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-3 gap-3">
            <Stat
              label="Chord tones"
              value={`${(analysis.metrics.chord_tone_pct * 100).toFixed(0)}%`}
            />
            <Stat
              label="Tensions"
              value={`${(analysis.metrics.tension_pct * 100).toFixed(0)}%`}
            />
            <Stat label="Total notes" value={analysis.metrics.total_notes} />
          </div>

          {analysis.ii_v_i.length > 0 && (
            <div>
              <h3 className="font-serif text-sm mb-1">ii-V-I Progressions</h3>
              <ul className="space-y-1">
                {analysis.ii_v_i.map((ev, i) => (
                  <li key={i} className="text-muted">
                    {ev.chords.join(" → ")}
                    {ev.key_guess && (
                      <span className="ml-1">(key: {ev.key_guess})</span>
                    )}
                    <span className="ml-1 text-xs">
                      [{ev.start_sec.toFixed(1)}s–{ev.end_sec.toFixed(1)}s]
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-border rounded p-3 text-center">
      <div className="text-lg font-serif">{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}
