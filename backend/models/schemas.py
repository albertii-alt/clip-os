from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Campaigns ──────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str
    creator_handle: Optional[str] = None
    platform: str
    payout_per_1k: Optional[float] = None
    min_clip_length: int = 30
    max_clip_length: int = 60
    required_hashtags: List[str] = []
    required_tags: List[str] = []
    forbidden_topics: List[str] = []
    style_notes: Optional[str] = None
    layout_style: str = 'full_bleed'
    boxed_background_color: str = 'black'


class CampaignUpdate(CampaignCreate):
    pass


class Campaign(CampaignCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Jobs ───────────────────────────────────────────────────
class JobCreate(BaseModel):
    source_type: str
    source_url: Optional[str] = None
    campaign_id: Optional[str] = None


class Job(BaseModel):
    id: str
    campaign_id: Optional[str]
    source_type: str
    source_url: Optional[str]
    original_filename: Optional[str]
    storage_path: Optional[str]
    status: str
    error_message: Optional[str]
    transcript_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Clips ──────────────────────────────────────────────────
class ClipUpdate(BaseModel):
    views: Optional[int] = None
    earnings: Optional[float] = None


class Clip(BaseModel):
    id: str
    job_id: str
    clip_index: int
    start_time: float
    end_time: float
    hook: Optional[str]
    category: Optional[str]
    viral_score: Optional[int]
    score_reason: Optional[str]
    storage_path: Optional[str]
    public_url: Optional[str]
    views: int
    earnings: float
    created_at: datetime

    class Config:
        from_attributes = True