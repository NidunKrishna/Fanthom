"""Validate API bodies and describe the video fields returned to clients."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReactionRequest(BaseModel):
    """A reaction to a video; identity always comes from the verified JWT."""
    model_config = ConfigDict(extra='forbid')
    video_id: str = Field(min_length=1, max_length=256)
    reaction: Literal['like', 'dislike', 'none']


class VideoResponse(BaseModel):
    """Public video metadata plus the current user's saved reaction."""
    id: str
    title: str
    description: str = ''
    category: str = ''
    creators: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    playback_url: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    published_at: str | None = None
    reaction: Literal['like', 'dislike'] | None = None


class VideoListResponse(BaseModel):
    """An ordered list of recommendations; internal vectors are never returned."""
    videos: list[VideoResponse]
