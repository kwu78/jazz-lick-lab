import os
import logging

from fastapi import UploadFile

from config import settings

logger = logging.getLogger(__name__)


def save_audio(job_id: str, file: UploadFile) -> str:
    job_dir = os.path.join(settings.data_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)
    audio_path = os.path.join(job_dir, "audio.mp3")
    with open(audio_path, "wb") as f:
        f.write(file.file.read())
    logger.info("Saved audio for job %s -> %s", job_id, audio_path)
    return audio_path
