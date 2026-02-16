import { useState, useEffect } from "react";
import Panel from "./Panel";
import Button from "./Button";
import ErrorBox from "./ErrorBox";
import {
  createPracticePack,
  listPracticePacks,
  downloadPracticePackUrl,
  type PracticePackArtifact,
} from "../api/jobs";

interface Props {
  jobId: string;
  selectionId: string | null;
}

export default function PracticePackPanel({ jobId, selectionId }: Props) {
  const [packs, setPacks] = useState<PracticePackArtifact[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listPracticePacks(jobId)
      .then((r) => setPacks(r.practice_packs))
      .catch(() => {});
  }, [jobId]);

  async function handleGenerate() {
    if (!selectionId) return;
    setGenerating(true);
    setError("");
    try {
      await createPracticePack(jobId, selectionId);
      const res = await listPracticePacks(jobId);
      setPacks(res.practice_packs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <Panel title="Practice Packs">
      {error && <ErrorBox message={error} />}

      <div className="mb-4">
        <Button
          onClick={handleGenerate}
          disabled={generating || !selectionId}
        >
          {generating ? "Generating..." : "Generate Practice Pack"}
        </Button>
        {!selectionId && (
          <span className="text-xs text-muted ml-2">
            Select a region first
          </span>
        )}
      </div>

      {packs.length > 0 && (
        <ul className="space-y-2">
          {packs.map((p) => (
            <li
              key={p.artifact_id}
              className="flex items-center justify-between border border-border rounded px-3 py-2 text-sm"
            >
              <div>
                <span className="text-muted">
                  {p.keys.length} keys
                </span>
                <span className="text-xs text-muted ml-2">
                  {new Date(p.created_at).toLocaleString()}
                </span>
              </div>
              <a
                href={downloadPracticePackUrl(jobId, p.artifact_id)}
                className="text-ink underline text-sm"
              >
                Download
              </a>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
