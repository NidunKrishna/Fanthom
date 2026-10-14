# Graph schema and application mapping

The catalog uses `(Creator)-[:CREATED]->(Video)-[:HAS_TOPIC]->(Topic)`.
The last read-only inspection found 11 videos, 11 creators, 82 topics, 11 CREATED
edges and 83 HAS_TOPIC edges. These counts are a snapshot, not application limits.

Videos are keyed by string `video_id` and supply title, description, category,
hashtags, view/like counts, and published_at. Creator and topic names enrich
ranking tags. The loader reads only Neo4j; the CSV catalog has been removed.

## Profiles and reactions

Successful login upserts `(User {username, name, created_at})`. A uniqueness
constraint prevents duplicate usernames. `ADMIN_DISPLAY_NAME` supplies the name,
falling back to `ADMIN_USERNAME`. Authentication still uses one configured account.

```text
(User)-[:LIKED {updated_at}]->(Video)
(User)-[:DISLIKED {updated_at}]->(Video)
```

Reactions are exclusive per user/video. Switching replaces the old edge in one
transaction; neutral feedback removes it. The user identity comes from the JWT.
Existing catalog-wide like_count is separate from personal feedback.

## Video URLs

Add an HTTPS URL to each video's `link` property. The loader also recognizes
`playback_url`, `video_url`, `video_link`, and `url` as fallbacks and returns it as
`playback_url`. No playback links existed in the latest live verification. The adapter now uses a YouTube watch URL for missing links when video_id matches the 11-character YouTube ID format; sample IDs such as abc123 remain previews.

The feed supports YouTube embeds, direct video file playback, and external HTTPS
watch links. Missing URLs remain previews. The backend polls graph changes every 10 seconds. The open feed also checks every 10 seconds and appends newly recommended entries.

See [BACKEND_GUIDE.md](BACKEND_GUIDE.md) for API contracts, ranking, and setup.
