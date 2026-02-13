from typing import List

from pydantic import BaseModel

from schemas.transcription import NoteEvent, ChordEvent


class LickRequest(BaseModel):
    start_sec: float
    end_sec: float


class LickSelection(BaseModel):
    start_sec: float
    end_sec: float
    notes: List[NoteEvent]
    chords: List[ChordEvent]
