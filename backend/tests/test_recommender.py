"""Verify preference ranking, exclusions, and degenerate catalog handling."""
from app.services.recommender import VideoRecommender

VIDEOS = [
    {'id': 'music', 'title': 'Guitar music'},
    {'id': 'python/one', 'title': 'Python pipelines', 'description': 'airflow engineering'},
    {'id': 'python-two', 'title': 'Python engineering', 'description': 'airflow pipelines'},
]


def test_feedback_personalizes_and_related_excludes_selected():
    engine = VideoRecommender(VIDEOS)
    assert engine.recommend({})[0]['id'] == 'music'
    ranked = engine.recommend({'python/one': 'like', 'music': 'dislike'})
    assert ranked[0]['id'] == 'python/one'
    assert all(video['id'] != 'music' for video in ranked)
    assert engine.recommend({}, video_id='python/one')[0]['id'] == 'python-two'
    assert engine.recommend({'python/one': 'dislike', 'python-two': 'dislike'})[0]['id'] == 'music'


def test_empty_catalog_and_empty_vocabulary():
    assert VideoRecommender([]).recommend({}) == []
    assert VideoRecommender([{'id': 'empty', 'title': ''}]).recommend({})[0]['id'] == 'empty'
