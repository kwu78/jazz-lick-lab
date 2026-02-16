import { useRef, useEffect, useState, useCallback } from "react";
import { OpenSheetMusicDisplay } from "opensheetmusicdisplay";

interface BaseProps {
  zoom?: number;
}

interface ArtifactMode extends BaseProps {
  jobId: string;
  artifactId: string;
  keyName: string;
  baseUrl: string;
  musicXmlUrl?: never;
}

interface UrlMode extends BaseProps {
  musicXmlUrl: string;
  jobId?: never;
  artifactId?: never;
  keyName?: never;
  baseUrl?: never;
}

type Props = ArtifactMode | UrlMode;

const ZOOM_PRESETS = [0.6, 0.8, 1.0, 1.2] as const;

export default function ScoreViewer(props: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null);
  const [zoom, setZoom] = useState(props.zoom ?? 1.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Derive the fetch URL from props
  const fetchUrl = props.musicXmlUrl
    ? props.musicXmlUrl
    : `${props.baseUrl}/jobs/${props.jobId}/practice-pack/${props.artifactId}/keys/${encodeURIComponent(props.keyName!)}/musicxml`;

  const loadScore = useCallback(async () => {
    if (!containerRef.current) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(fetchUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const xml = await res.text();

      containerRef.current.innerHTML = "";
      const osmd = new OpenSheetMusicDisplay(containerRef.current, {
        autoResize: true,
        drawTitle: false,
        drawComposer: false,
        drawCredits: false,
      });
      osmd.setLogLevel("warn");

      await osmd.load(xml);
      osmd.Zoom = zoom;
      osmd.render();
      osmdRef.current = osmd;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load score");
      osmdRef.current = null;
    } finally {
      setLoading(false);
    }
  }, [fetchUrl, zoom]);

  useEffect(() => {
    loadScore();
  }, [loadScore]);

  useEffect(() => {
    const osmd = osmdRef.current;
    if (osmd) {
      osmd.Zoom = zoom;
      osmd.render();
    }
  }, [zoom]);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-muted">Zoom:</span>
        {ZOOM_PRESETS.map((z) => (
          <button
            key={z}
            onClick={() => setZoom(z)}
            className={`px-2 py-0.5 text-xs border rounded ${
              zoom === z
                ? "border-ink bg-ink text-page"
                : "border-border text-muted hover:border-ink"
            }`}
          >
            {z === 1.0 ? "1×" : `${z}×`}
          </button>
        ))}
      </div>

      {loading && (
        <p className="text-sm text-muted py-4 text-center">
          Loading score...
        </p>
      )}

      {error && (
        <p className="text-sm text-red-700 py-4 text-center">{error}</p>
      )}

      <div
        ref={containerRef}
        className="bg-white border border-border rounded p-4 min-h-[200px]"
      />
    </div>
  );
}
