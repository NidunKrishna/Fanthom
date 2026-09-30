"""
Simple content-based video recommender.

Builds a TF-IDF matrix over each video's tags/description/category and
uses cosine similarity to recommend videos similar to ones a user liked
or watched. Falls back to trending/popular videos for new users
(cold-start problem).
"""
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "videos.csv"


class VideoRecommender:
    def __init__(self, csv_path: str = DATA_PATH):
        self.df = pd.read_csv(csv_path)
        self.df["content"] = (
            self.df["title"] + " " + self.df["tags"] + " " + self.df["category"]
        )
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["content"])
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
        self.id_to_index = {vid: idx for idx, vid in enumerate(self.df["id"])}

    def all_videos(self):
        return self.df.to_dict(orient="records")

    def get_video(self, video_id: int):
        row = self.df[self.df["id"] == video_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def recommend_for_video(self, video_id: int, top_n: int = 5):
        """Videos similar to a single given video (content-based)."""
        if video_id not in self.id_to_index:
            return []
        idx = self.id_to_index[video_id]
        scores = list(enumerate(self.similarity_matrix[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        recommendations = []
        for i, score in scores:
            if self.df.iloc[i]["id"] == video_id:
                continue
            recommendations.append(self.df.iloc[i].to_dict())
            if len(recommendations) >= top_n:
                break
        return recommendations

    def recommend_for_user(self, liked_video_ids, top_n: int = 8):
        """
        Aggregate recommendations based on all videos a user has liked/watched.
        If the user has no history, return trending (first N) videos instead.
        """
        liked_video_ids = [v for v in liked_video_ids if v in self.id_to_index]
        if not liked_video_ids:
            return self.trending(top_n)

        indices = [self.id_to_index[v] for v in liked_video_ids]
        agg_scores = self.similarity_matrix[indices].mean(axis=0)

        scored = list(enumerate(agg_scores))
        scored = sorted(scored, key=lambda x: x[1], reverse=True)

        recommendations = []
        seen = set(liked_video_ids)
        for i, score in scored:
            vid = self.df.iloc[i]["id"]
            if vid in seen:
                continue
            recommendations.append(self.df.iloc[i].to_dict())
            seen.add(vid)
            if len(recommendations) >= top_n:
                break
        return recommendations

    def trending(self, top_n: int = 8):
        """Cold-start fallback: just return a sample of videos."""
        return self.df.head(top_n).to_dict(orient="records")

    def search(self, query: str):
        query = query.lower().strip()
        if not query:
            return []
        mask = self.df["content"].str.lower().str.contains(query)
        return self.df[mask].to_dict(orient="records")
