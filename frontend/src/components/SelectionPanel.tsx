import { useState, useEffect } from "react";
import Panel from "./Panel";
import Button from "./Button";
import Input from "./Input";
import ErrorBox from "./ErrorBox";
import {
  createSelection,
  listSelections,
  type Selection,
} from "../api/jobs";

interface Props {
  jobId: string;
  regionStart: number | null;
  regionEnd: number | null;
  activeSelection: Selection | null;
  onSelect: (s: Selection) => void;
}

export default function SelectionPanel({
  jobId,
  regionStart,
  regionEnd,
  activeSelection,
  onSelect,
}: Props) {
  const [selections, setSelections] = useState<Selection[]>([]);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listSelections(jobId).then((r) => setSelections(r.selections)).catch(() => {});
  }, [jobId]);

  async function handleSave() {
    if (regionStart == null || regionEnd == null) return;
    setSaving(true);
    setError("");
    try {
      const res = await createSelection(jobId, {
        name: name || undefined,
        start_sec: +regionStart.toFixed(2),
        end_sec: +regionEnd.toFixed(2),
      });
      setSelections((prev) => [...prev, res.selection]);
      onSelect(res.selection);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel title="Selections">
      {error && <ErrorBox message={error} />}
      <div className="flex items-end gap-2 mb-4">
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1">Name (optional)</label>
          <Input
            type="text"
            placeholder="e.g. Intro lick"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-border rounded px-3 py-1.5 text-sm bg-transparent"
          />
        </div>
        <Button
          onClick={handleSave}
          disabled={saving || regionStart == null}
        >
          {saving ? "Saving..." : "Save Selection"}
        </Button>
      </div>

      {selections.length > 0 && (
        <ul className="space-y-1">
          {selections.map((s) => (
            <li
              key={s.selection_id}
              onClick={() => onSelect(s)}
              className={`text-sm px-3 py-2 rounded cursor-pointer border transition-colors ${
                activeSelection?.selection_id === s.selection_id
                  ? "border-ink bg-ink/5"
                  : "border-transparent hover:bg-ink/5"
              }`}
            >
              <span className="font-medium">
                {s.name || "Untitled"}
              </span>
              <span className="text-muted ml-2">
                {s.start_sec.toFixed(2)}s &ndash; {s.end_sec.toFixed(2)}s
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
