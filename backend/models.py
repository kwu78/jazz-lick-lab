import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default="CREATED")
    instrument = Column(String, nullable=False)
    audio_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    error = Column(Text, nullable=True)
