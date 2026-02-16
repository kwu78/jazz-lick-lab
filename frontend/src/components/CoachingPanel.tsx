import { useState, useEffect } from "react";
import Panel from "./Panel";
import ErrorBox from "./ErrorBox";
import { getCoaching, type Coaching } from "../api/jobs";

interface Props {
  jobId: string;
  selectionId: string | null;
}

export default function CoachingPanel({ jobId, selectionId }: Props) {
  const [coaching, setCoaching] = useState<Coaching | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selectionId) {
      setCoaching(null);
      return;
    }
    setLoading(true);
    setError("");
    getCoaching(jobId, selectionId)
      .then(setCoaching)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed"))
      .finally(() => setLoading(false));
  }, [jobId, selectionId]);

  if (!selectionId) {
    return (
      <Panel title="Coaching">
        <p className="text-sm text-muted">Select a region for coaching.</p>
      </Panel>
    );
  }

  return (
    <Panel title="Coaching">
      {error && <ErrorBox message={error} />}
      {loading && <p className="text-sm text-muted">Loading...</p>}
      {coaching && (
        <div className="space-y-4 text-sm">
          <p>{coaching.summary}</p>

          <div>
            <h3 className="font-serif text-sm mb-1">Why It Works</h3>
            <p className="text-muted">{coaching.why_it_works}</p>
          </div>

          <div>
            <h3 className="font-serif text-sm mb-1">Practice Steps</h3>
            <ol className="list-decimal list-inside space-y-1 text-muted">
              {coaching.practice_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>

          <div>
            <h3 className="font-serif text-sm mb-1">Variation Idea</h3>
            <p className="text-muted">{coaching.variation_idea}</p>
          </div>

          <div>
            <h3 className="font-serif text-sm mb-1">Listening Tip</h3>
            <p className="text-muted">{coaching.listening_tip}</p>
          </div>

          {coaching.flags.length > 0 && (
            <div className="flex gap-2">
              {coaching.flags.map((f) => (
                <span
                  key={f}
                  className="text-xs px-2 py-0.5 rounded border border-border text-muted"
                >
                  {f}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
