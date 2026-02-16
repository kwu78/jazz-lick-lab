import { useState, useEffect } from "react";
import Panel from "./Panel";
import Button from "./Button";
import ErrorBox from "./ErrorBox";
import ScoreViewer from "./ScoreViewer";
import {
  createPracticePack,
  listPracticePacks,
  downloadPracticePackUrl,
  type PracticePackArtifact,
} from "../api/jobs";
import { BASE_URL } from "../api/client";

interface Props {
  jobId: string;
  selectionId: string | null;
}

export default function PracticePackPanel({ jobId, selectionId }: Props) {
  const [packs, setPacks] = useState<PracticePackArtifact[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  // Score viewer state
  const [selectedPackIdx, setSelectedPackIdx] = useState(0);
  const [selectedKey, setSelectedKey] = useState("");

  useEffect(() => {
    listPracticePacks(jobId)
      .then((r) => setPacks(r.practice_packs))
      .catch(() => {});
  }, [jobId]);

  // When packs change or selection changes, default the key
  useEffect(() => {
    const pack = packs[selectedPackIdx];
    if (pack && pack.keys_included.length > 0) {
      setSelectedKey((prev) =>
        pack.keys_included.includes(prev) ? prev : pack.keys_included[0]
      );
    }
  }, [packs, selectedPackIdx]);

  async function handleGenerate() {
    if (!selectionId) return;
    setGenerating(true);
    setError("");
    try {
      await createPracticePack(jobId, selectionId);
      const res = await listPracticePacks(jobId);
      setPacks(res.practice_packs);
      // Select the newly created pack (last one)
      setSelectedPackIdx(res.practice_packs.length - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const activePack = packs[selectedPackIdx] ?? null;

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
        <ul className="space-y-2 mb-6">
          {packs.map((p, i) => (
            <li
              key={p.artifact_id}
              className="flex items-center justify-between border border-border rounded px-3 py-2 text-sm"
            >
              <div>
                <span className="text-muted">
                  {p.keys_included.length} keys
                </span>
                <span className="text-xs text-muted ml-2">
                  {new Date(p.created_at).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedPackIdx(i)}
                  className={`text-xs underline ${
                    selectedPackIdx === i ? "text-ink font-bold" : "text-muted"
                  }`}
                >
                  View Score
                </button>
                <a
                  href={downloadPracticePackUrl(jobId, p.artifact_id)}
                  download
                  className="text-ink underline text-sm"
                >
                  Download
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}

      {activePack && (
        <div>
          <h3 className="font-serif text-base mb-3 pb-2 border-b border-border tracking-widest uppercase">
            Score
          </h3>

          <div className="flex items-center gap-3 mb-4">
            {packs.length > 1 && (
              <label className="flex items-center gap-1.5 text-xs text-muted">
                Pack:
                <select
                  value={selectedPackIdx}
                  onChange={(e) => setSelectedPackIdx(Number(e.target.value))}
                  className="border border-border rounded px-2 py-1 text-xs bg-page text-ink"
                >
                  {packs.map((p, i) => (
                    <option key={p.artifact_id} value={i}>
                      #{i + 1} — {p.keys_included.length} keys
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label className="flex items-center gap-1.5 text-xs text-muted">
              Key:
              <select
                value={selectedKey}
                onChange={(e) => setSelectedKey(e.target.value)}
                className="border border-border rounded px-2 py-1 text-xs bg-page text-ink"
              >
                {activePack.keys_included.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selectedKey && (
            <ScoreViewer
              jobId={jobId}
              artifactId={activePack.artifact_id}
              keyName={selectedKey}
              baseUrl={BASE_URL}
            />
          )}
        </div>
      )}
    </Panel>
  );
}
