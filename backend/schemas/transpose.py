from typing import List, Optional

from pydantic import BaseModel

from schemas.transcription import NoteEvent, ChordEvent


class TransposeRequest(BaseModel):
    start_sec: float
    end_sec: float
    target_key: str
    source_key: Optional[str] = None


class TransposeResponse(BaseModel):
    start_sec: float
    end_sec: float
    source_key: str
    target_key: str
    interval_semitones: int
    notes: List[NoteEvent]
    chords: List[ChordEvent]
