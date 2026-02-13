from typing import List, Optional

from pydantic import BaseModel


class NoteEvent(BaseModel):
    pitch_midi: int
    start_sec: float
    duration_sec: float


class ChordEvent(BaseModel):
    symbol: str
    start_sec: float
    end_sec: Optional[float] = None


class TranscriptionResult(BaseModel):
    notes: List[NoteEvent]
    chords: List[ChordEvent]
