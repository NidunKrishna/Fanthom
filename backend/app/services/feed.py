"""Coordinate cached graph metadata, fresh user preferences, and ranking."""
import logging
from threading import Event, Lock, Thread
from time import monotonic

from .recommender import VideoRecommender


class FeedService:
    """Poll graph metadata and cache vectors; read preferences per request."""

    def __init__(self, repository, poll_seconds=10):
        """Inject persistence and initialize an empty, process-local catalog cache."""
        self.repository = repository
        self._engine = None
        self._loaded_at = 0
        self._lock = Lock()
        self.poll_seconds = poll_seconds
        self._stop = Event()
        self._worker = None

    def refresh(self):
        """Read graph records and rebuild vectors only when catalog data changes."""
        with self._lock:
            records = self.repository.videos()
            if self._engine is None or records != self._engine.videos:
                self._engine = VideoRecommender(records)
            self._loaded_at = monotonic()

    def start(self):
        """Start one background poller; database outages do not stop future polls."""
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = Thread(target=self._poll, name='graph-catalog-poller', daemon=True)
        self._worker.start()

    def _poll(self):
        """Refresh immediately, then wait between completed reads without overlap."""
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception:
                logging.getLogger(__name__).warning('Catalog refresh failed; retrying on the next poll.')
            if self._stop.wait(self.poll_seconds):
                break

    def stop(self):
        """Signal shutdown and allow an in-flight read to finish without new polls."""
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=5)

    def engine(self):
        """Return the latest snapshot, loading on demand if no poller has filled it."""
        if self._engine is None or (self._worker is None and monotonic() - self._loaded_at >= self.poll_seconds):
            self.refresh()
        return self._engine

    def recommendations(self, username, video_id=None):
        """Rank a feed or related videos and attach the user's persisted reactions."""
        engine = self.engine()
        if video_id is not None and video_id not in engine.id_to_index:
            raise LookupError('Video not found.')
        preferences = self.repository.preferences(username)
        videos = engine.recommend(preferences, video_id=video_id, limit=5 if video_id else 8)
        return [{**video, 'reaction': preferences.get(video['id'])} for video in videos]
