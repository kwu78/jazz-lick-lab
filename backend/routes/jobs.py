import uuid
import logging

import redis
from rq import Queue
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Job
from services.storage import save_audio
from workers.tasks import process_job

router = APIRouter()
logger = logging.getLogger(__name__)


def _job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "instrument": job.instrument,
        "audio_path": job.audio_path,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "result_json": job.result_json,
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
    return _job_to_dict(job)
