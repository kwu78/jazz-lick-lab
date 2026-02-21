import { useState } from "react";

interface Props {
  pdfUrl: string;
}

export default function PdfViewer({ pdfUrl }: Props) {
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  if (error) {
    return (
      <p className="text-xs text-muted py-4 text-center">
        PDF not available (ensure transcription requested outputs include pdf).
      </p>
    );
  }

  return (
    <>
      {loading && (
        <p className="text-sm text-muted py-4 text-center">Loading PDF...</p>
      )}
      <iframe
        src={pdfUrl}
        className="w-full border border-border rounded bg-white"
        style={{ height: 700, display: loading ? "none" : "block" }}
        onLoad={() => setLoading(false)}
        onError={() => {
          setLoading(false);
          setError(true);
        }}
      />
    </>
  );
}
