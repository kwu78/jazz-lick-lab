import math
import uuid
import logging
from datetime import datetime, timezone
from typing import List

import redis
from rq import Queue
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from config import settings
from database import get_db
from models import Job
from schemas.analysis import AnalysisResponse
from schemas.lick import LickRequest, LickSelection
from schemas.selection import (
    SelectionCreateRequest,
    SelectionCreateResponse,
    SelectionListResponse,
    SelectionRecord,
)
from schemas.settings import JobSettings, SettingsUpdateRequest, SettingsResponse
from schemas.transcription import TranscriptionResult, NoteEvent, ChordEvent
from schemas.transpose import TransposeRequest, TransposeResponse
from services.analysis import compute_coverage, detect_ii_v_i
from services.coach_factory import get_coach_provider
from services.storage import save_audio
from services.theory import (
    parse_chord_root,
    parse_key,
    semitone_interval,
    transpose_chord_symbol,
)
from workers.tasks import process_job

router = APIRouter()
logger = logging.getLogger(__name__)


def _job_to_dict(job: Job, validated_result: dict | None = None) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "instrument": job.instrument,
        "audio_path": job.audio_path,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "result_json": validated_result,
        "error": job.error,
    }


@router.post("/jobs")
def create_job(
    audio: UploadFile = File(...),
    instrument: str = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    job_id = str(uuid.uuid4())
    audio_path = save_audio(job_id, audio)

    job = Job(
        id=job_id,
        status="CREATED",
        instrument=instrument,
        audio_path=audio_path,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    conn = redis.from_url(settings.redis_url)
    q = Queue(connection=conn)
    q.enqueue(process_job, job_id)

    logger.info("Created and enqueued job %s (instrument=%s)", job_id, instrument)
    return _job_to_dict(job)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    validated_result = None
    validated_settings = None
    if job.result_json is not None:
        try:
            validated_result = TranscriptionResult(**job.result_json).model_dump()
        except ValidationError as exc:
            logger.error("Job %s: invalid transcription schema: %s", job_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Invalid transcription schema in result_json",
            )

        raw_settings = job.result_json.get("settings")
        if raw_settings is not None:
            try:
                validated_settings = JobSettings(**raw_settings).model_dump()
            except ValidationError as exc:
                logger.error("Job %s: invalid settings schema: %s", job_id, exc)
                raise HTTPException(
                    status_code=500,
                    detail="Invalid settings schema in result_json",
                )

    result = _job_to_dict(job, validated_result=validated_result)
    result["settings"] = validated_settings
    return result


def _validate_time_range(start_sec: float, end_sec: float) -> None:
    if start_sec < 0 or end_sec < 0:
        raise HTTPException(status_code=400, detail="start_sec and end_sec must be non-negative")
    if end_sec <= start_sec:
        raise HTTPException(status_code=400, detail="end_sec must be greater than start_sec")


def _load_transcription(job_id: str, db: Session) -> tuple[Job, TranscriptionResult]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.result_json is None:
        raise HTTPException(status_code=400, detail="Job has no transcription result")
    try:
        transcription = TranscriptionResult(**job.result_json)
    except ValidationError as exc:
        logger.error("Job %s: invalid transcription schema: %s", job_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Invalid transcription schema in result_json",
        )
    return job, transcription


def _load_ready_transcription_with_settings(
    job_id: str, db: Session
) -> tuple[Job, TranscriptionResult, JobSettings]:
    """Load a READY job, validate transcription + settings, return all three."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "READY" or job.result_json is None:
        raise HTTPException(status_code=400, detail="No transcription available for this job")
    try:
        transcription = TranscriptionResult(**job.result_json)
    except ValidationError as exc:
        logger.error("Job %s: invalid transcription schema: %s", job_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Invalid transcription schema in result_json",
        )
    raw_settings = job.result_json.get("settings")
    if raw_settings is not None:
        try:
            job_settings = JobSettings(**raw_settings)
        except ValidationError as exc:
            logger.error("Job %s: invalid settings schema: %s", job_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Invalid settings schema in result_json",
            )
    else:
        job_settings = JobSettings()
    return job, transcription, job_settings


def _extract_lick(
    transcription: TranscriptionResult, start_sec: float, end_sec: float
) -> tuple[list[NoteEvent], list[ChordEvent]]:
    notes = [
        n for n in transcription.notes
        if n.start_sec < end_sec and (n.start_sec + n.duration_sec) > start_sec
    ]
    chords = [
        c for c in transcription.chords
        if c.start_sec < end_sec and (c.end_sec is None or c.end_sec > start_sec)
    ]
    return notes, chords


@router.post("/jobs/{job_id}/lick")
def select_lick(
    job_id: str,
    req: LickRequest,
    db: Session = Depends(get_db),
) -> dict:
    _validate_time_range(req.start_sec, req.end_sec)
    _, transcription = _load_transcription(job_id, db)
    notes, chords = _extract_lick(transcription, req.start_sec, req.end_sec)

    selection = LickSelection(
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        notes=notes,
        chords=chords,
    )
    return selection.model_dump()


@router.post("/jobs/{job_id}/transpose")
def transpose_lick(
    job_id: str,
    req: TransposeRequest,
    db: Session = Depends(get_db),
) -> dict:
    _validate_time_range(req.start_sec, req.end_sec)

    try:
        parse_key(req.target_key)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid target_key: {req.target_key!r}")

    _, transcription = _load_transcription(job_id, db)
    notes, chords = _extract_lick(transcription, req.start_sec, req.end_sec)

    # Determine source key
    source_key = req.source_key
    if source_key is None:
        if not chords:
            raise HTTPException(
                status_code=400,
                detail="source_key required when no chords are available",
            )
        root = parse_chord_root(chords[0].symbol)
        if root is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot parse root from chord: {chords[0].symbol!r}",
            )
        source_key = root

    try:
        parse_key(source_key)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source_key: {source_key!r}")

    interval = semitone_interval(source_key, req.target_key)

    transposed_notes = [
        NoteEvent(
            pitch_midi=n.pitch_midi + interval,
            start_sec=n.start_sec,
            duration_sec=n.duration_sec,
        )
        for n in notes
    ]

    transposed_chords = [
        ChordEvent(
            symbol=transpose_chord_symbol(c.symbol, interval),
            start_sec=c.start_sec,
            end_sec=c.end_sec,
        )
        for c in chords
    ]

    response = TransposeResponse(
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        source_key=source_key,
        target_key=req.target_key,
        interval_semitones=interval,
        notes=transposed_notes,
        chords=transposed_chords,
    )
    return response.model_dump()


@router.post("/jobs/{job_id}/settings")
def update_settings(
    job_id: str,
    req: SettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "READY" or job.result_json is None:
        raise HTTPException(status_code=400, detail="No transcription available for this job")

    try:
        TranscriptionResult(**job.result_json)
    except ValidationError as exc:
        logger.error("Job %s: invalid transcription schema: %s", job_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Invalid transcription schema in result_json",
        )

    # Merge settings: only overwrite fields that were provided
    existing_settings = job.result_json.get("settings", {}) or {}
    updates = req.model_dump(exclude_none=True)
    merged = {**existing_settings, **updates}

    try:
        validated = JobSettings(**merged)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Persist back into result_json
    updated = {**job.result_json, "settings": validated.model_dump()}
    job.result_json = updated
    flag_modified(job, "result_json")
    db.commit()

    return SettingsResponse(
        job_id=job.id,
        settings=validated,
    ).model_dump()


@router.post("/jobs/{job_id}/selection")
def create_selection(
    job_id: str,
    req: SelectionCreateRequest,
    db: Session = Depends(get_db),
) -> dict:
    _validate_time_range(req.start_sec, req.end_sec)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "READY" or job.result_json is None:
        raise HTTPException(status_code=400, detail="No transcription available for this job")

    try:
        TranscriptionResult(**job.result_json)
    except ValidationError as exc:
        logger.error("Job %s: invalid transcription schema: %s", job_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Invalid transcription schema in result_json",
        )

    record = SelectionRecord(
        selection_id=str(uuid.uuid4()),
        name=req.name,
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    existing = job.result_json.get("selections", []) or []
    existing.append(record.model_dump())

    updated = {**job.result_json, "selections": existing}
    job.result_json = updated
    flag_modified(job, "result_json")
    db.commit()

    return SelectionCreateResponse(
        job_id=job.id,
        selection=record,
    ).model_dump()


@router.get("/jobs/{job_id}/selection")
def list_selections(
    job_id: str,
    db: Session = Depends(get_db),
) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.result_json is None:
        return SelectionListResponse(job_id=job.id, selections=[]).model_dump()

    raw_selections = job.result_json.get("selections", []) or []

    validated = []
    for raw in raw_selections:
        try:
            validated.append(SelectionRecord(**raw))
        except ValidationError as exc:
            logger.error("Job %s: invalid selection schema: %s", job_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Invalid selection schema in result_json",
            )

    return SelectionListResponse(
        job_id=job.id,
        selections=validated,
    ).model_dump()


@router.get("/jobs/{job_id}/analysis")
def get_analysis(
    job_id: str,
    selection_id: str,
    db: Session = Depends(get_db),
) -> dict:
    job, transcription = _load_transcription(job_id, db)

    # Validate and find selection
    raw_selections = job.result_json.get("selections", []) or []
    matched = None
    for raw in raw_selections:
        try:
            rec = SelectionRecord(**raw)
        except ValidationError as exc:
            logger.error("Job %s: invalid selection schema: %s", job_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Invalid selection schema in result_json",
            )
        if rec.selection_id == selection_id:
            matched = rec
            break

    if matched is None:
        raise HTTPException(status_code=404, detail="Selection not found")

    notes, chords = _extract_lick(transcription, matched.start_sec, matched.end_sec)

    metrics = compute_coverage(notes, chords)
    ii_v_i = detect_ii_v_i(chords)

    response = AnalysisResponse(
        job_id=job.id,
        selection_id=selection_id,
        window_start_sec=matched.start_sec,
        window_end_sec=matched.end_sec,
        metrics=metrics,
        ii_v_i=ii_v_i,
    )
    return response.model_dump()


@router.get("/jobs/{job_id}/coaching")
def get_coaching(
    job_id: str,
    selection_id: str,
    db: Session = Depends(get_db),
) -> dict:
    job, transcription = _load_transcription(job_id, db)

    # Validate and find selection
    raw_selections = job.result_json.get("selections", []) or []
    matched = None
    for raw in raw_selections:
        try:
            rec = SelectionRecord(**raw)
        except ValidationError as exc:
            logger.error("Job %s: invalid selection schema: %s", job_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Invalid selection schema in result_json",
            )
        if rec.selection_id == selection_id:
            matched = rec
            break

    if matched is None:
        raise HTTPException(status_code=404, detail="Selection not found")

    notes, chords = _extract_lick(transcription, matched.start_sec, matched.end_sec)

    metrics = compute_coverage(notes, chords)
    ii_v_i = detect_ii_v_i(chords)

    analysis = AnalysisResponse(
        job_id=job.id,
        selection_id=selection_id,
        window_start_sec=matched.start_sec,
        window_end_sec=matched.end_sec,
        metrics=metrics,
        ii_v_i=ii_v_i,
    )

    coach = get_coach_provider()
    coaching = coach.generate(analysis)
    return coaching.model_dump()


@router.get("/jobs/{job_id}/notes")
def get_notes(job_id: str, db: Session = Depends(get_db)) -> dict:
    job, transcription, job_settings = _load_ready_transcription_with_settings(job_id, db)
    offset = job_settings.offset_sec

    notes = [
        NoteEvent(
            pitch_midi=n.pitch_midi,
            start_sec=n.start_sec - offset,
            duration_sec=n.duration_sec,
        )
        for n in transcription.notes
    ]
    return {"job_id": job.id, "notes": [n.model_dump() for n in notes]}


@router.get("/jobs/{job_id}/chords")
def get_chords(job_id: str, db: Session = Depends(get_db)) -> dict:
    job, transcription, job_settings = _load_ready_transcription_with_settings(job_id, db)
    offset = job_settings.offset_sec

    chords = [
        ChordEvent(
            symbol=c.symbol,
            start_sec=c.start_sec - offset,
            end_sec=(c.end_sec - offset) if c.end_sec is not None else None,
        )
        for c in transcription.chords
    ]
    return {"job_id": job.id, "chords": [c.model_dump() for c in chords]}


@router.put("/jobs/{job_id}/chords")
def update_chords(
    job_id: str,
    incoming: List[ChordEvent],
    db: Session = Depends(get_db),
) -> dict:
    job, transcription, job_settings = _load_ready_transcription_with_settings(job_id, db)
    offset = job_settings.offset_sec

    # Validate symbols and convert display-time → raw-time
    raw_chords = []
    for c in incoming:
        if not c.symbol or not c.symbol.strip():
            raise HTTPException(status_code=400, detail="Chord symbol must be a non-empty string")
        raw_start = c.start_sec + offset
        raw_end = (c.end_sec + offset) if c.end_sec is not None else None
        if not math.isfinite(raw_start):
            raise HTTPException(status_code=400, detail="start_sec must be finite")
        if raw_end is not None and raw_end <= raw_start:
            raise HTTPException(status_code=400, detail="end_sec must be greater than start_sec")
        raw_chords.append(ChordEvent(symbol=c.symbol, start_sec=raw_start, end_sec=raw_end))

    # Sort by start_sec for consistency
    raw_chords.sort(key=lambda c: c.start_sec)

    # Persist: replace chords in result_json, keep everything else
    updated = {**job.result_json, "chords": [c.model_dump() for c in raw_chords]}
    job.result_json = updated
    flag_modified(job, "result_json")
    db.commit()

    # Return in display-time (same as GET /chords)
    display_chords = [
        ChordEvent(
            symbol=c.symbol,
            start_sec=c.start_sec - offset,
            end_sec=(c.end_sec - offset) if c.end_sec is not None else None,
        )
        for c in raw_chords
    ]
    return {"job_id": job.id, "chords": [c.model_dump() for c in display_chords]}
