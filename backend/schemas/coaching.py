from typing import List, Optional

from pydantic import BaseModel


class CoachingResponse(BaseModel):
    summary: str
    why_it_works: str
    practice_steps: List[str]
    variation_idea: str
    listening_tip: str
    rationale: Optional[str] = None
    flags: List[str] = []
