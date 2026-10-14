"""Protected endpoints for personalized graph feeds and persisted feedback."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import me
from ..schemas import ReactionRequest, VideoListResponse

router = APIRouter(prefix='/api/videos', tags=['Video recommendations'])


@router.get('', response_model=VideoListResponse)
def recommendations(request: Request, video_id: str | None = Query(default=None, min_length=1, max_length=256), user: dict = Depends(me)):
    """Return personalized videos or videos related to one selected graph ID."""
    try:
        videos = request.app.state.feed.recommendations(user['username'], video_id)
    except LookupError:
        raise HTTPException(404, 'Video not found.') from None
    return {'videos': videos}


@router.post('/reaction')
def react(payload: ReactionRequest, request: Request, user: dict = Depends(me)):
    """Save/remove only the authenticated user's reaction in a graph transaction."""
    saved = request.app.state.repository.react(user['username'], payload.video_id, payload.reaction)
    if not saved:
        raise HTTPException(404, 'User or video not found. Please sign in again if needed.')
    return {'video_id': payload.video_id, 'reaction': None if payload.reaction == 'none' else payload.reaction}
