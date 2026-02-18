import logging
import statistics

from sqlalchemy.orm.attributes import flag_modified

from database import SessionLocal
from models import Job
from services.klangio import transcribe

logger = logging.getLogger(__name__)


def _compute_settings_from_beats(beat_tracking: list) -> dict:
    """Derive bpm, offset_sec, time_signature from Klangio beat tracking.

    beat_tracking is a list of [timestamp_sec, downbeat_value] pairs,
    e.g. [[0.14, 1.0], [0.76, 2.0], [1.35, 3.0], [1.95, 4.0], ...].
    """
    if not beat_tracking or len(beat_tracking) < 4:
        return {}

    timestamps = [b[0] for b in beat_tracking]
    downbeat_values = [b[1] for b in beat_tracking]

    # BPM from median of inter-beat intervals
    diffs = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    diffs = [d for d in diffs if d > 0.1]  # filter out glitches
    if not diffs:
        return {}
    bpm = round(60.0 / statistics.median(diffs), 1)

    # Time signature: numerator = max downbeat value (e.g. 4.0 → 4/4)
    numerator = int(max(downbeat_values))
    if numerator < 2:
        numerator = 4
    time_signature = f"{numerator}/4"

    # Offset: first timestamp where downbeat_value == 1.0
    offset_sec = 0.0
    for ts, dv in beat_tracking:
        if dv == 1.0:
            offset_sec = round(ts, 4)
            break

    return {
        "bpm": bpm,
        "offset_sec": offset_sec,
        "time_signature": time_signature,
    }


def _auto_detect_settings(result: dict) -> dict:
    """Build settings from MusicInfo (primary) with beat tracking as fallback."""
    tempo_bpm = result.get("tempo_bpm")
    time_sig = result.get("time_signature")
    audio_offset = result.get("audio_offset_sec")

    # Primary: MusicInfo-derived values (same timebase as note positions)
    settings: dict = {}
    if tempo_bpm is not None and 30 <= tempo_bpm <= 300:
        settings["bpm"] = round(tempo_bpm, 1)
    if time_sig:
        settings["time_signature"] = time_sig
    if audio_offset is not None:
        settings["offset_sec"] = round(audio_offset, 4)

    # Fallback: beat tracking (if MusicInfo didn't provide usable values)
    beat_tracking = result.get("beat_tracking")
    if beat_tracking:
        bt_settings = _compute_settings_from_beats(beat_tracking)

        # Log drift diagnostic between MusicInfo and beat tracking
        if bt_settings.get("bpm") and settings.get("bpm"):
            drift = abs(bt_settings["bpm"] - settings["bpm"])
            logger.info(
                "BPM drift: MusicInfo=%.1f beat_tracking=%.1f diff=%.1f",
                settings["bpm"], bt_settings["bpm"], drift,
            )

        # Fill gaps: only use beat tracking for fields MusicInfo didn't provide
        if "bpm" not in settings and "bpm" in bt_settings:
            settings["bpm"] = bt_settings["bpm"]
        if "time_signature" not in settings and "time_signature" in bt_settings:
            settings["time_signature"] = bt_settings["time_signature"]
        if "offset_sec" not in settings and "offset_sec" in bt_settings:
            settings["offset_sec"] = bt_settings["offset_sec"]

    if settings:
        settings.setdefault("offset_sec", 0.0)
        settings.setdefault("time_signature", "4/4")
        logger.info(
            "Auto-detected settings: bpm=%s time_sig=%s offset=%s",
            settings.get("bpm"), settings.get("time_signature"),
            settings.get("offset_sec"),
        )

    return settings


def process_job(job_id: str) -> None:
    db = SessionLocal()
    job = None
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %s not found", job_id)
            return

        job.status = "TRANSCRIBING"
        db.commit()
        logger.info("Job %s: TRANSCRIBING", job_id)

        result = transcribe(job.audio_path, job.instrument)

        job.result_json = result
        job.status = "READY"

        # Auto-detect settings (only if user hasn't already set them)
        existing_settings = result.get("settings") or {}
        user_set_bpm = existing_settings.get("bpm") is not None

        if not user_set_bpm:
            detected = _auto_detect_settings(result)
            if detected:
                # Merge: keep any user-set fields, fill in detected ones
                merged = {**detected, **{k: v for k, v in existing_settings.items() if v is not None}}
                job.result_json = {**result, "settings": merged}
                flag_modified(job, "result_json")
                logger.info("Job %s: auto-populated settings", job_id)

        db.commit()
        logger.info("Job %s: READY", job_id)

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        try:
            if job is not None:
                job.status = "FAILED"
                job.error = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
