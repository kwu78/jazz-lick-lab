from typing import List, Optional

from pydantic import BaseModel


class SelectionCreateRequest(BaseModel):
    name: Optional[str] = None
    start_sec: float
    end_sec: float


class SelectionRecord(BaseModel):
    selection_id: str
    name: Optional[str] = None
    start_sec: float
    end_sec: float
    created_at: str


class SelectionCreateResponse(BaseModel):
    job_id: str
    selection: SelectionRecord


class SelectionListResponse(BaseModel):
    job_id: str
    selections: List[SelectionRecord]
