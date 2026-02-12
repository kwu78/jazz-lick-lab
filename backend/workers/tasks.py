import logging

from database import SessionLocal
from models import Job
from services.klangio import transcribe

logger = logging.getLogger(__name__)


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
