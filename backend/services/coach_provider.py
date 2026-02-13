from typing import Protocol

from schemas.analysis import AnalysisResponse
from schemas.coaching import CoachingResponse


class CoachProvider(Protocol):
    def generate(self, analysis: AnalysisResponse) -> CoachingResponse: ...
