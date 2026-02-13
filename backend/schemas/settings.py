import math
import re
from typing import Optional

from pydantic import BaseModel, field_validator

_TIME_SIG_RE = re.compile(r"^([1-9]\d*)/([1-9]\d*)$")


class JobSettings(BaseModel):
    bpm: Optional[float] = None
    offset_sec: float = 0.0
    time_signature: Optional[str] = None

    @field_validator("bpm")
    @classmethod
    def bpm_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("bpm must be greater than 0")
        return v

    @field_validator("offset_sec")
    @classmethod
    def offset_must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("offset_sec must be a finite number")
        return v

    @field_validator("time_signature")
    @classmethod
    def time_signature_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _TIME_SIG_RE.match(v):
            raise ValueError("time_signature must match format 'N/D' (e.g. '4/4', '3/4')")
        return v


class SettingsUpdateRequest(BaseModel):
    bpm: Optional[float] = None
    offset_sec: Optional[float] = None
    time_signature: Optional[str] = None

    @field_validator("bpm")
    @classmethod
    def bpm_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("bpm must be greater than 0")
        return v

    @field_validator("offset_sec")
    @classmethod
    def offset_must_be_finite(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("offset_sec must be a finite number")
        return v

    @field_validator("time_signature")
    @classmethod
    def time_signature_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _TIME_SIG_RE.match(v):
            raise ValueError("time_signature must match format 'N/D' (e.g. '4/4', '3/4')")
        return v


class SettingsResponse(BaseModel):
    job_id: str
    settings: JobSettings
