"""
YouTube Data API v3 wrapper with quota-aware batching and caching.

Quota costs:
  search.list  = 100 units
  videos.list  =   1 unit
  channels.list =  1 unit
"""

import os
import re
import isodate
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from deep_translator import GoogleTranslator
import database as db

# European + English language codes
ALLOWED_LANGUAGES = {
    "en", "es", "fr", "de", "it", "pt", "nl", "sv", "da", "no", "nb", "nn",
    "fi", "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sr", "sl", "lt", "lv",
    "et", "el", "ga", "mt", "ca", "eu", "gl", "is", "mk", "sq", "bs", "uk",
}

MIN_VIEWS = 10_000

_translator = None

def _get_translator():
    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source="auto", target="en")
    return _translator


def _translate_to_english(text: str, lang: str) -> str:
    """Translate text to English if not already English."""
    if not text or lang in ("en", "en-US", "en-GB", "en-AU", "en-CA"):
        return text
    try:
        translated = _get_translator().translate(text[:5000])
        return translated or text
    except Exception as e:
        print(f"[Translate] Error: {e}")
        return text


def _get_language(snippet: dict) -> str | None:
    """Extract language code from video snippet."""
    lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or ""
    return lang.split("-")[0].lower() if lang else None

_youtube = None


def get_client():
    global _youtube
    if _youtube is None:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise RuntimeError("YOUTUBE_API_KEY not set")
        _youtube = build("youtube", "v3", developerKey=api_key)
    return _youtube


def _parse_duration(iso_duration: str) -> int:
    """Return duration in seconds from ISO 8601 duration string."""
    try:
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception:
        return 0


def _best_thumbnail(thumbnails: dict) -> str:
    for q in ("maxres", "standard", "high", "medium", "default"):
        if q in thumbnails:
            return thumbnails[q]["url"]
    return ""


QUOTA_CAP = 3000  # stop refreshing if we've used this much today


def search_videos(keyword: str, days_back: int = 14, max_results: int = 15) -> list[str]:
    """
    Search for videos matching keyword published in the last `days_back` days.
    Returns list of video IDs. Costs 100 quota units per duration bucket.
    max_results capped at 15 to save quota.
    """
    # Check quota cap before searching
    quota = db.get_quota_used()
    if quota["units_used"] >= QUOTA_CAP:
        print(f"[YouTube] Quota cap reached ({quota['units_used']}/{QUOTA_CAP}), skipping search for '{keyword}'")
        return []

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    yt = get_client()
    try:
        resp = yt.search().list(
            part="id",
            q=keyword,
            type="video",
            publishedAfter=published_after,
            videoDuration="medium",   # 4-20 minutes
            maxResults=max_results,
            order="viewCount",
            relevanceLanguage="en",
        ).execute()
        db.log_quota(100)
    except HttpError as e:
        print(f"[YouTube] search error for '{keyword}': {e}")
        return []

    ids = [item["id"]["videoId"] for item in resp.get("items", [])]

    # Also search for "long" videos (>20 min) — only if quota allows
    quota = db.get_quota_used()
    if quota["units_used"] < QUOTA_CAP:
        try:
            resp2 = yt.search().list(
                part="id",
                q=keyword,
                type="video",
                publishedAfter=published_after,
                videoDuration="long",
                maxResults=max_results,
                order="viewCount",
                relevanceLanguage="en",
            ).execute()
            db.log_quota(100)
            ids += [item["id"]["videoId"] for item in resp2.get("items", [])]
        except HttpError as e:
            print(f"[YouTube] search (long) error for '{keyword}': {e}")

    return list(set(ids))


def fetch_video_details(video_ids: list[str]) -> list[dict]:
    """
    Fetch full details for up to 50 video IDs per call.
    Filters out Shorts (<= 120 seconds).
    Costs 1 unit per call (batched up to 50).
    """
    if not video_ids:
        return []

    results = []
    yt = get_client()

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = yt.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            ).execute()
            db.log_quota(1)
        except HttpError as e:
            print(f"[YouTube] videos.list error: {e}")
            continue

        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})

            duration_str = content.get("duration", "PT0S")
            duration_secs = _parse_duration(duration_str)

            # Skip Shorts (<=120s)
            if duration_secs <= 120:
                continue

            # Skip videos under 10K views
            view_count = int(stats.get("viewCount", 0))
            if view_count < MIN_VIEWS:
                continue

            # Language filter: only English + European languages
            lang = _get_language(snippet)
            if lang and lang not in ALLOWED_LANGUAGES:
                continue

            title = snippet.get("title", "")
            description = snippet.get("description", "")

            # Translate non-English titles/descriptions to English
            if lang and lang != "en":
                title = _translate_to_english(title, lang)
                description = _translate_to_english(description, lang)

            thumbnails = snippet.get("thumbnails", {})
            results.append({
                "video_id": item["id"],
                "title": title,
                "description": description,
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "duration": duration_str,
                "duration_seconds": duration_secs,
                "view_count": view_count,
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail_url": _best_thumbnail(thumbnails),
                "channel_id": snippet.get("channelId", ""),
                "channel_name": snippet.get("channelTitle", ""),
                "original_language": lang or "en",
            })

    return results


def fetch_channel_stats(channel_ids: list[str]) -> dict[str, dict]:
    """
    Fetch subscriber counts for channels (batched, 50 per call).
    Costs 1 unit per call.
    Returns dict of channel_id -> {subscriber_count, channel_name}.
    """
    result = {}
    yt = get_client()

    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        try:
            resp = yt.channels().list(
                part="snippet,statistics",
                id=",".join(batch),
            ).execute()
            db.log_quota(1)
        except HttpError as e:
            print(f"[YouTube] channels.list error: {e}")
            continue

        for item in resp.get("items", []):
            stats = item.get("statistics", {})
            result[item["id"]] = {
                "channel_name": item["snippet"].get("title", ""),
                "subscriber_count": int(stats.get("subscriberCount", 0))
                if not stats.get("hiddenSubscriberCount", False)
                else 0,
            }

    return result


def fetch_channel_recent_videos(channel_id: str, max_results: int = 20) -> list[dict]:
    """
    Fetch recent uploads from a channel to calculate average views.
    Costs 100 (search) + 1 (videos.list) = 101 units.
    Uses channel's uploads playlist for efficiency (costs 1 unit instead of 100).
    """
    yt = get_client()

    # Get uploads playlist ID from channel
    try:
        ch_resp = yt.channels().list(
            part="contentDetails",
            id=channel_id,
        ).execute()
        db.log_quota(1)
    except HttpError as e:
        print(f"[YouTube] channel contentDetails error: {e}")
        return []

    items = ch_resp.get("items", [])
    if not items:
        return []

    uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"].get("uploads", "")
    if not uploads_playlist:
        return []

    # Fetch recent uploads from playlist
    try:
        pl_resp = yt.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=max_results,
        ).execute()
        db.log_quota(1)
    except HttpError as e:
        print(f"[YouTube] playlistItems error: {e}")
        return []

    video_ids = [
        item["contentDetails"]["videoId"]
        for item in pl_resp.get("items", [])
    ]

    if not video_ids:
        return []

    # Fetch stats for those videos
    try:
        v_resp = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        ).execute()
        db.log_quota(1)
    except HttpError as e:
        print(f"[YouTube] videos.list (channel avg) error: {e}")
        return []

    result = []
    for item in v_resp.get("items", []):
        content = item.get("contentDetails", {})
        duration_secs = _parse_duration(content.get("duration", "PT0S"))
        # Exclude Shorts from the baseline average
        if duration_secs <= 60:
            continue
        stats = item.get("statistics", {})
        result.append({
            "video_id": item["id"],
            "title": item["snippet"].get("title", ""),
            "view_count": int(stats.get("viewCount", 0)),
            "published_at": item["snippet"].get("publishedAt", ""),
        })

    return result


def get_channel_data(channel_id: str, channel_name: str = "") -> dict:
    """
    Returns channel data with subscriber count and avg views.
    Uses 24h cache. If not cached, fetches from API.
    """
    cached = db.get_cached_channel(channel_id)
    if cached:
        return cached

    # Fetch subscriber count
    ch_stats = fetch_channel_stats([channel_id])
    ch = ch_stats.get(channel_id, {})
    subscriber_count = ch.get("subscriber_count", 0)
    name = ch.get("channel_name", channel_name)

    # Fetch recent videos for avg views
    recent = fetch_channel_recent_videos(channel_id, max_results=20)
    view_counts = [v["view_count"] for v in recent if v["view_count"] > 0]
    avg_views = sum(view_counts) / len(view_counts) if view_counts else 0.0
    last_video_titles = [
        {"title": v["title"], "view_count": v["view_count"]}
        for v in recent[:10]
    ]

    db.upsert_channel(channel_id, name, subscriber_count, avg_views, last_video_titles)

    return {
        "channel_id": channel_id,
        "channel_name": name,
        "subscriber_count": subscriber_count,
        "avg_views": avg_views,
        "last_video_titles": last_video_titles,
    }
