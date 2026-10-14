"""Rank graph videos using TF-IDF text similarity and saved user feedback."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VideoRecommender:
    """Keep ranking independent from HTTP, Neo4j, files, and user authentication."""

    def __init__(self, records):
        """Build a sparse text matrix from title, description, tags, and category."""
        self.videos = [dict(video) for video in records]
        self.id_to_index = {video['id']: index for index, video in enumerate(self.videos)}
        content = [' '.join(str(video.get(key) or '') for key in ('title', 'description', 'tags', 'category')) for video in self.videos]
        self.matrix = None
        if content:
            try:
                self.matrix = TfidfVectorizer(stop_words='english').fit_transform(content)
            except ValueError as error:
                if 'empty vocabulary' not in str(error):
                    raise

    def recommend(self, preferences, video_id=None, limit=8):
        """Rank by liked similarity minus disliked similarity; hide disliked videos.

        A selected video adds its similarity as the primary related-video signal.
        Already-liked videos remain available so users can revisit/change feedback.
        Cold-start and equal-score results retain graph popularity order. Similarity
        is computed against preference/selected rows, avoiding a dense N x N matrix.
        """
        if not self.videos:
            return []
        scores = np.zeros(len(self.videos))
        if self.matrix is not None:
            for reaction, weight in (('like', 1.0), ('dislike', -1.0)):
                indices = [self.id_to_index[key] for key, value in preferences.items() if value == reaction and key in self.id_to_index]
                if indices:
                    scores += weight * cosine_similarity(self.matrix[indices], self.matrix).mean(axis=0)
            if video_id in self.id_to_index:
                scores += 2 * cosine_similarity(self.matrix[self.id_to_index[video_id]], self.matrix).ravel()
        ranked = sorted(range(len(self.videos)), key=lambda index: scores[index], reverse=True)
        return [self.videos[index] for index in ranked
                if self.videos[index]['id'] != video_id
                and preferences.get(self.videos[index]['id']) != 'dislike'][:limit]
