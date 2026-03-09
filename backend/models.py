from pydantic import BaseModel
from typing import Optional, List


class KeywordAdd(BaseModel):
    keyword: str


class SaveVideoRequest(BaseModel):
    notes: Optional[str] = ""


class UpdateNotesRequest(BaseModel):
    notes: str


class VideoSummary(BaseModel):
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    published_at: str
    view_count: int
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    thumbnail_url: Optional[str] = ""
    duration_seconds: Optional[int] = 0
    outlier_score: Optional[float] = 0.0
    view_to_sub_ratio: Optional[float] = 0.0
    view_to_average_ratio: Optional[float] = 0.0
    is_breakout: Optional[bool] = False
    is_saved: Optional[bool] = False
    subscriber_count: Optional[int] = 0
    avg_views: Optional[float] = 0.0
    keywords_matched: Optional[List[str]] = []


class RefreshResponse(BaseModel):
    videos_processed: int
    breakouts_found: int
    quota_used: int
    message: str
