import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import PageShell from "../components/PageShell";
import Panel from "../components/Panel";
import Button from "../components/Button";
import ErrorBox from "../components/ErrorBox";
import { createJob } from "../api/jobs";

const INSTRUMENTS = ["bass", "piano", "guitar", "vocals", "drums"] as const;

export default function UploadPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [instrument, setInstrument] = useState("bass");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Please select an audio file.");
      return;
    }
    setError("");
    setUploading(true);
    try {
      const job = await createJob(file, instrument || undefined);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <PageShell>
      <div className="max-w-md mx-auto mt-12">
        <h2 className="font-serif text-3xl mb-2 text-center">
          Upload a Lick
        </h2>
        <p className="text-muted text-sm text-center mb-8">
          Upload an audio file to transcribe and analyze.
        </p>

        {error && <ErrorBox message={error} />}

        <Panel>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm mb-1">Audio file</label>
              <input
                ref={fileRef}
                type="file"
                accept="audio/*"
                className="block w-full text-sm text-muted file:mr-3 file:px-3 file:py-1.5 file:rounded file:border file:border-border file:bg-transparent file:text-ink file:text-sm file:cursor-pointer"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Instrument</label>
              <select
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
                className="w-full border border-border rounded px-3 py-2 text-sm bg-transparent text-ink cursor-pointer"
              >
                {INSTRUMENTS.map((inst) => (
                  <option key={inst} value={inst}>
                    {inst.charAt(0).toUpperCase() + inst.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" disabled={uploading}>
              {uploading ? "Uploading..." : "Upload & Transcribe"}
            </Button>
          </form>
        </Panel>
      </div>
    </PageShell>
  );
}
