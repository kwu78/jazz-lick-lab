import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read from environment)
# ---------------------------------------------------------------------------
_api_key: str | None = os.getenv("KLANGIO_API_KEY")
_base_url: str = os.getenv("KLANGIO_BASE_URL", "https://api.klang.io").rstrip("/")
_model: str = os.getenv("KLANGIO_MODEL", "universal")
_poll_interval: int = int(os.getenv("KLANGIO_POLL_INTERVAL_SEC", "2"))
_poll_timeout: int = int(os.getenv("KLANGIO_POLL_TIMEOUT_SEC", "180"))

_BOUNDARY = "----KlangioFormBoundary9f3c2a"
_TERMINAL = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})


def _require_api_key() -> str:
    if not _api_key:
        raise RuntimeError("KLANGIO_API_KEY not configured")
    return _api_key


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no new dependencies)
# ---------------------------------------------------------------------------

def _multipart_body(
    audio_path: str, extra_fields: dict[str, str] | None = None
) -> tuple[bytes, str]:
    """Build a multipart/form-data body with the audio file + optional fields."""
    parts: list[bytes] = []

    for name, value in (extra_fields or {}).items():
        parts.append(
            f"--{_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f"\r\n"
            f"{value}\r\n"
            .encode()
        )

    filename = Path(audio_path).name
    ext = Path(audio_path).suffix.lower()
    mime = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac",
        ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    }.get(ext, "application/octet-stream")

    with open(audio_path, "rb") as fh:
        file_bytes = fh.read()

    parts.append(
        f"--{_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n"
        f"\r\n"
        .encode()
        + file_bytes
        + b"\r\n"
    )

    parts.append(f"--{_BOUNDARY}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={_BOUNDARY}"


def _request(
    method: str, path: str, *, body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    """Authenticated Klangio API request → raw response bytes."""
    url = f"{_base_url}{path}"
    hdrs: dict[str, str] = {"kl-api-key": _require_api_key()}
    if headers:
        hdrs.update(headers)

    req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"Klangio API {exc.code} on {method} {path}: {err}"
        ) from exc


def _post_json(path: str, body: bytes, content_type: str) -> dict:
    raw = _request("POST", path, body=body, headers={"Content-Type": content_type})
    return json.loads(raw)


def _get_json(path: str) -> dict:
    raw = _request("GET", path)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Core Klangio API functions
# ---------------------------------------------------------------------------

def submit_transcription(audio_path: str) -> str:
    """Upload audio and create a Klangio transcription job. Returns job_id."""
    body, ct = _multipart_body(audio_path, extra_fields={"outputs": "midi"})
    model = urllib.parse.quote(_model)
    data = _post_json(f"/transcription?model={model}", body, ct)

    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError(f"Klangio did not return job_id: {list(data.keys())}")

    logger.info("Klangio transcription job submitted: %s", job_id)
    return str(job_id)


def _submit_chord_recognition(audio_path: str) -> str:
    """Upload audio and create a Klangio chord recognition job. Returns job_id."""
    body, ct = _multipart_body(audio_path)
    data = _post_json("/chord-recognition?vocabulary=full", body, ct)

    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError("Klangio chord-recognition did not return job_id")

    logger.info("Klangio chord-recognition job submitted: %s", job_id)
    return str(job_id)


def poll_status(klangio_job_id: str) -> tuple[str, str | None]:
    """Check Klangio job status. Returns (status, error_message)."""
    data = _get_json(f"/job/{klangio_job_id}/status")
    status = data.get("status", "UNKNOWN")
    if status == "FAILED":
        logger.error("Klangio status response for %s: %s", klangio_job_id, data)
    error = data.get("error_message") or data.get("error") or data.get("message")
    return status, error


def fetch_result_json(klangio_job_id: str) -> dict:
    """Download JSON result for a completed Klangio job."""
    raw = _request("GET", f"/job/{klangio_job_id}/json")
    return json.loads(raw)


def _poll_until_terminal(job_id: str, label: str) -> tuple[str, str | None]:
    """Block-poll a Klangio job until terminal status or timeout.

    Returns (status, error_message).
    """
    deadline = time.monotonic() + _poll_timeout
    while True:
        status, error_msg = poll_status(job_id)
        logger.info("Klangio %s %s → %s%s", label, job_id, status,
                     f" ({error_msg})" if error_msg else "")
        if status in _TERMINAL:
            return status, error_msg
        if time.monotonic() >= deadline:
            raise RuntimeError("Klangio job timed out")
        time.sleep(_poll_interval)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

def adapt_klangio_json_to_transcription_result(
    payload: dict, chord_payload: list | dict | None = None,
) -> dict:
    """Map Klangio JSON to our TranscriptionResult schema.

    Klangio transcription payload structure::

        {
          "MusicInfo": {"Tempo": 88.0, "TimeSignature": "4/4", "AudioOffset": 28.42},
          "Parts": [{"Measures": [{"Voices": [{"Notes": [...]}]}]}]
        }

    Each note: {"Midi": [42], "Duration": 0.25, ...}
      - Midi is a list (supports chords); -1 = rest
      - Duration is a fraction of the measure (0.25 = quarter note in 4/4)

    Chord payload is a list of [start_sec, end_sec, symbol] tuples.

    Returns::

        {
          "notes":  [{"pitch_midi": int, "start_sec": float, "duration_sec": float}, ...],
          "chords": [{"symbol": str, "start_sec": float, "end_sec": float|None}, ...],
          "audio_offset": float
        }
    """
    music_info = payload.get("MusicInfo", {})
    tempo = float(music_info.get("Tempo", 120.0))
    time_sig = str(music_info.get("TimeSignature", "4/4"))
    audio_offset = float(music_info.get("AudioOffset", 0.0))

    beats_per_measure = int(time_sig.split("/")[0])
    measure_sec = (beats_per_measure / tempo) * 60.0

    # --- Notes ---
    notes: list[dict] = []
    for part in payload.get("Parts", []):
        measure_start = audio_offset
        for measure in part.get("Measures", []):
            for voice in measure.get("Voices", []):
                pos = 0.0  # position within measure (0..1)
                for n in voice.get("Notes", []):
                    midi_vals = n.get("Midi", [-1])
                    dur_frac = float(n.get("Duration", 0.0))
                    dur_sec = dur_frac * measure_sec
                    start_sec = measure_start + pos * measure_sec

                    for midi in midi_vals:
                        if midi >= 0:
                            notes.append({
                                "pitch_midi": int(midi),
                                "start_sec": round(start_sec, 4),
                                "duration_sec": round(dur_sec, 4),
                            })

                    pos += dur_frac
            measure_start += measure_sec

    # --- Chords ---
    chords: list[dict] = []
    chord_src = chord_payload if chord_payload is not None else []
    if isinstance(chord_src, list):
        for c in chord_src:
            if isinstance(c, list) and len(c) >= 3:
                sym = str(c[2])
                if sym.upper() in ("N", "N.C.", "NC", "NONE"):
                    continue
                chords.append({
                    "symbol": sym,
                    "start_sec": round(float(c[0]), 4),
                    "end_sec": round(float(c[1]), 4),
                })
    elif isinstance(chord_src, dict):
        for c in chord_src.get("chords", []):
            sym = str(c.get("symbol", ""))
            start = c.get("start_sec") or c.get("start")
            end = c.get("end_sec") or c.get("end")
            if not sym or start is None:
                continue
            if sym.upper() in ("N", "N.C.", "NC", "NONE"):
                continue
            chords.append({
                "symbol": sym,
                "start_sec": round(float(start), 4),
                "end_sec": round(float(end), 4) if end is not None else None,
            })

    return {"notes": notes, "chords": chords, "audio_offset": audio_offset}


# ---------------------------------------------------------------------------
# Public entry point (called by workers/tasks.py)
# ---------------------------------------------------------------------------

def transcribe(audio_path: str, instrument: str) -> dict:
    """Full Klangio transcription pipeline.

    Submits a transcription job (notes) and a chord recognition job,
    polls both to completion, fetches results, and returns a dict
    matching our TranscriptionResult schema.
    """
    logger.info(
        "Starting Klangio transcription: audio_path=%s instrument=%s",
        audio_path, instrument,
    )

    # 1. Submit transcription job
    transcription_id = submit_transcription(audio_path)

    # 2. Submit chord recognition (best-effort; failure → empty chords)
    chord_id: str | None = None
    try:
        chord_id = _submit_chord_recognition(audio_path)
    except Exception as exc:
        logger.warning("Chord recognition submission failed, continuing without: %s", exc)

    # 3. Poll transcription to completion
    status, error_msg = _poll_until_terminal(transcription_id, "transcription")
    if status == "FAILED":
        raise RuntimeError(f"Klangio job failed: {error_msg or 'unknown error'}")
    if status != "COMPLETED":
        raise RuntimeError(f"Klangio transcription ended with status: {status}")

    # 4. Fetch transcription JSON
    transcription_payload = fetch_result_json(transcription_id)

    # 5. Poll + fetch chord recognition (best-effort)
    chord_payload: dict | None = None
    if chord_id is not None:
        try:
            chord_status, chord_err = _poll_until_terminal(chord_id, "chord-recognition")
            if chord_status == "COMPLETED":
                chord_payload = fetch_result_json(chord_id)
            else:
                logger.warning(
                    "Chord recognition ended with status: %s (%s)",
                    chord_status, chord_err,
                )
        except Exception as exc:
            logger.warning("Chord recognition failed, continuing without: %s", exc)

    # 6. Adapt to our schema and return
    result = adapt_klangio_json_to_transcription_result(
        transcription_payload, chord_payload
    )
    logger.info(
        "Transcription complete: %d notes, %d chords",
        len(result["notes"]), len(result["chords"]),
    )
    return result
