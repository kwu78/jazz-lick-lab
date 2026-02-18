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
    tempo_bpm: Optional[float] = None
    time_signature: Optional[str] = None
    audio_offset_sec: Optional[float] = None
