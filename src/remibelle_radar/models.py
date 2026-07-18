from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Radar(StrEnum):
    X = "X Radar"
    INSTAGRAM = "Instagram Radar"
    TIKTOK = "TikTok Radar"
    SHOWROOM = "SHOWROOM Radar"


class Priority(StrEnum):
    S = "S級！！"
    A = "A"
    B = "B"
    REVIEW = "要確認"


class CandidateInput(BaseModel):
    display_name: str = Field(min_length=1)
    radar: Radar
    source_url: str
    source_text: str = ""
    source_is_self_post: bool | None = None
    x_url: str | None = None
    instagram_url: str | None = None
    instagram_status: str = "未確認"
    tiktok_url: str | None = None
    showroom_url: str | None = None
    other_profile_url: str | None = None
    age_text: str | None = None
    affiliation_text: str | None = None
    evidence: list[str] = Field(default_factory=list)
    discovered_at: datetime


class ClassifiedCandidate(BaseModel):
    candidate: CandidateInput
    priority: Priority
    score: int
    reason: str
    excluded_reason: str | None = None
    review_priority: str | None = None


class RadarResult(BaseModel):
    radar: Radar
    searched: int = 0
    added: int = 0
    duplicates: int = 0
    excluded: int = 0
    failures: int = 0
    s_count: int = 0
    errors: list[str] = Field(default_factory=list)
    unpersisted: list[str] = Field(default_factory=list)
