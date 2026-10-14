"""Persist user profiles, video metadata, and exclusive LIKED/DISLIKED edges."""
from threading import Lock
import re

CATALOG_QUERY = """
MATCH (v:Video)
OPTIONAL MATCH (creator:Creator)-[:CREATED]->(v)
WITH v, collect(DISTINCT creator.name) AS creators
OPTIONAL MATCH (v)-[:HAS_TOPIC]->(topic:Topic)
RETURN v.video_id AS id, v.title AS title, v.description AS description,
       v.category AS category, v.hashtags AS hashtags,
       v.view_count AS view_count, v.like_count AS like_count,
       coalesce(properties(v)['link'], properties(v)['playback_url'],
                properties(v)['video_url'], properties(v)['video_link'],
                properties(v)['url']) AS playback_url,
       v.published_at AS published_at, creators,
       collect(DISTINCT topic.name) AS topics
ORDER BY coalesce(v.view_count, 0) DESC, v.video_id
"""


class GraphRepository:
    """Expose graph operations without exposing Cypher to route handlers."""

    def __init__(self, database):
        """Inject the database client and track once-per-process schema setup."""
        self.database = database
        self._schema_ready = False
        self._schema_lock = Lock()

    def ensure_user(self, username, name):
        """Create/update one uniquely identified profile after successful sign-in."""
        with self._schema_lock:
            if not self._schema_ready:
                self.database.write('CREATE CONSTRAINT app_user_username IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE')
                self._schema_ready = True
        self.database.write('''
            MERGE (u:User {username: $username})
            ON CREATE SET u.created_at = datetime()
            SET u.name = $name
            RETURN u.username AS username
        ''', username=username, name=name)

    def videos(self):
        """Load only graph videos and flatten creator/topic metadata for ranking."""
        videos = []
        for record in self.database.read(CATALOG_QUERY):
            if not record['id']:
                continue
            video = dict(record)
            video['id'] = str(video['id'])
            link = video.get('playback_url')
            if not link or not str(link).strip():
                video['playback_url'] = ('https://www.youtube.com/watch?v=' + video['id']) if re.fullmatch(r'[A-Za-z0-9_-]{11}', video['id']) else None
            video['title'] = video['title'] or 'Untitled video'
            video['description'] = video['description'] or ''
            video['category'] = str(video['category'] or '')
            hashtags = video.pop('hashtags') or []
            if isinstance(hashtags, str):
                hashtags = [hashtags]
            video['tags'] = ' '.join([*hashtags, *video['topics'], *video['creators']])
            videos.append(video)
        # Preserve popularity order within each group, keeping sample IDs last.
        return sorted(videos, key=lambda video: not bool(video.get('playback_url')))

    def preferences(self, username):
        """Return the authenticated user's saved reaction for each video ID."""
        rows = self.database.read('''
            MATCH (u:User {username: $username})-[r:LIKED|DISLIKED]->(v:Video)
            RETURN v.video_id AS id, type(r) AS reaction
        ''', username=username)
        return {str(row['id']): 'like' if row['reaction'] == 'LIKED' else 'dislike' for row in rows}

    def react(self, username, video_id, reaction):
        """Atomically replace a user's reaction, or remove it for neutral feedback.

        Updating the user locks that node before reading/deleting existing edges,
        serializing concurrent reactions from that user. Relationship types come
        from a fixed mapping; all user-provided values remain query parameters.
        """
        relationship = {'like': 'LIKED', 'dislike': 'DISLIKED', 'none': None}[reaction]
        create = f'MERGE (u)-[r:{relationship}]->(v) SET r.updated_at = datetime()' if relationship else ''
        rows = self.database.write('''
            MATCH (u:User {username: $username})
            SET u.feedback_updated_at = datetime()
            WITH u
            MATCH (v:Video {video_id: $video_id})
            OPTIONAL MATCH (u)-[previous:LIKED|DISLIKED]->(v)
            WITH u, v, collect(previous) AS previous_edges
            FOREACH (edge IN previous_edges | DELETE edge)
        ''' + create + '\nRETURN v.video_id AS id', username=username, video_id=video_id)
        return bool(rows)
