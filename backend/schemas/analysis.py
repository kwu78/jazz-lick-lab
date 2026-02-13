from typing import List, Optional

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    selection_id: str


class CoverageMetrics(BaseModel):
    total_notes: int
    chord_tone_notes: int
    tension_notes: int
    other_notes: int
    chord_tone_pct: float
    tension_pct: float


class IiVIEvent(BaseModel):
    start_sec: float
    end_sec: float
    chords: List[str]
    key_guess: Optional[str] = None


class AnalysisResponse(BaseModel):
    job_id: str
    selection_id: str
    window_start_sec: float
    window_end_sec: float
    metrics: CoverageMetrics
    ii_v_i: List[IiVIEvent]
