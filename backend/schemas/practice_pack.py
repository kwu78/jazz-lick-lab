from typing import List, Optional

from pydantic import BaseModel

from schemas.transcription import NoteEvent, ChordEvent


class PracticePackRequest(BaseModel):
    selection_id: str
    target_keys: Optional[List[str]] = None
    include_original: bool = True


class KeyEntry(BaseModel):
    key: str
    interval_semitones: int
    notes: List[NoteEvent]
    chords: List[ChordEvent]
    file_name: str
    musicxml_file_name: str


class PracticePackArtifact(BaseModel):
    artifact_id: str
    job_id: str
    selection_id: str
    source_key: str
    keys_included: List[str]
    dir_path: str
    zip_path: str
    created_at: str


class PracticePackResponse(BaseModel):
    job_id: str
    artifact: PracticePackArtifact


class PracticePackListResponse(BaseModel):
    job_id: str
    practice_packs: List[PracticePackArtifact]
