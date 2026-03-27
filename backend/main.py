import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

import database as db
import youtube_api as yt
import transcript as tr
import trends as tr_mod
import tiktok_trends as tt
import outlier as ol
from models import KeywordAdd, SaveVideoRequest, UpdateNotesRequest, TrackChannelRequest

db.init_db()

app = FastAPI(title="Outlier Detector", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_refresh_status = {"running": False, "progress": "", "last_done": None}


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Keywords ───────────────────────────────────────────────────────────────────

@app.get("/api/keywords")
def list_keywords():
    return db.get_keywords(active_only=False)


@app.post("/api/keywords")
def add_keyword(body: KeywordAdd):
    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(400, "Keyword cannot be empty")
    db.add_keyword(kw)
    return {"ok": True, "keyword": kw}


@app.delete("/api/keywords/{keyword}")
def remove_keyword(keyword: str):
    db.remove_keyword(keyword)
    return {"ok": True}


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    breakouts = db.get_breakout_videos(limit=30)
    recent = db.get_recent_videos(limit=30)
    keyword_summary = db.get_keyword_breakout_summary()
    quota = db.get_quota_used()
    stats = db.get_stats_summary()
    return {
        "breakout_videos": breakouts,
        "recent_videos": recent,
        "keyword_summary": [{"keyword": k, "count": c} for k, c in keyword_summary[:15]],
        "quota": quota,
        "stats": stats,
        "refresh_status": _refresh_status,
    }


# ── Videos with filtering ─────────────────────────────────────────────────────

@app.get("/api/videos")
def list_videos(
    breakout_only: bool = False,
    keyword: Optional[str] = None,
    channel_tier: Optional[str] = None,
    sort_by: str = "outlier_score",
    min_views: Optional[int] = None,
    min_sub_count: Optional[int] = None,
    max_sub_count: Optional[int] = None,
    limit: int = 50,
):
    return db.get_videos(
        limit=limit,
        keyword=keyword,
        breakout_only=breakout_only,
        channel_tier=channel_tier,
        sort_by=sort_by,
        min_views=min_views,
        min_sub_count=min_sub_count,
        max_sub_count=max_sub_count,
    )


@app.get("/api/videos/{video_id}")
def get_video(video_id: str):
    v = db.get_video_detail(video_id)
    if not v:
        raise HTTPException(404, "Video not found")

    v["title_analysis"] = ol.analyze_title(v.get("title", ""))
    v["description_analysis"] = ol.analyze_description(v.get("description", ""))
    v["channel_tier"] = ol.get_channel_tier(v.get("subscriber_count", 0))
    v["channel_tier_label"] = ol.CHANNEL_TIER_LABELS.get(v["channel_tier"], "Unknown")

    views = v.get("view_count", 0)
    likes = v.get("like_count", 0)
    comments = v.get("comment_count", 0)
    subs = v.get("subscriber_count") or 1
    avg = v.get("avg_views") or 1

    try:
        pub = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        days_up = max((datetime.now(timezone.utc) - pub).days, 1)
    except Exception:
        days_up = 1

    v["metrics"] = {
        "like_to_view_pct": round(likes / views * 100, 3) if views else 0,
        "comment_to_view_pct": round(comments / views * 100, 3) if views else 0,
        "view_to_sub_ratio": round(views / subs, 2) if subs > 0 else 0,
        "vs_channel_avg_multiplier": round(views / avg, 2) if avg > 0 else 0,
        "views_per_day": round(views / days_up),
        "days_since_upload": days_up,
        "engagement_rate": round((likes + comments) / views * 100, 3) if views else 0,
    }

    return v


@app.get("/api/videos/{video_id}/transcript")
def get_video_transcript(video_id: str):
    return tr.get_transcript(video_id)


# ── Export ─────────────────────────────────────────────────────────────────────

@app.get("/api/export/csv", response_class=PlainTextResponse)
def export_csv(breakout_only: bool = True):
    csv_data = db.export_videos_csv(breakout_only=breakout_only)
    if not csv_data:
        raise HTTPException(404, "No data to export")
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outlier-videos.csv"},
    )


# ── Refresh / Discovery ────────────────────────────────────────────────────────

@app.post("/api/refresh")
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    days_back: int = 14,
    keywords: Optional[str] = None,
):
    """Trigger a refresh. Optionally pass comma-separated keywords to refresh only those."""
    if _refresh_status["running"]:
        return {"ok": False, "message": "Refresh already running"}
    kw_filter = [k.strip() for k in keywords.split(",")] if keywords else None
    background_tasks.add_task(run_refresh, days_back, kw_filter)
    return {"ok": True, "message": "Refresh started"}


@app.post("/api/refresh-keyword")
def refresh_single_keyword(keyword: str, days_back: int = 14):
    """Synchronously refresh a single keyword. Works in serverless (Vercel)."""
    try:
        ids = yt.search_videos(keyword, days_back=days_back)
        if not ids:
            return {"ok": True, "keyword": keyword, "videos_processed": 0, "breakouts": 0}

        videos = yt.fetch_video_details(ids)
        breakouts = 0

        for v in videos:
            v["keywords_matched"] = [keyword]

            channel_id = v["channel_id"]
            try:
                ch_data = yt.get_channel_data(channel_id, v.get("channel_name", ""))
            except Exception:
                ch_data = {"subscriber_count": 0, "avg_views": 0.0}

            score_data = ol.compute_outlier_score(
                v["view_count"],
                ch_data.get("subscriber_count", 0),
                ch_data.get("avg_views", 0.0),
                published_at=v.get("published_at"),
                like_count=v.get("like_count", 0),
                comment_count=v.get("comment_count", 0),
            )

            db.upsert_video(v)
            db.upsert_outlier_score(
                v["video_id"],
                score_data["view_to_sub_ratio"],
                score_data["view_to_average_ratio"],
                score_data["outlier_score"],
                score_data["is_breakout"],
            )
            if score_data["is_breakout"]:
                breakouts += 1

        return {"ok": True, "keyword": keyword, "videos_processed": len(videos), "breakouts": breakouts}
    except Exception as e:
        import traceback
        return {"ok": False, "keyword": keyword, "error": str(e), "trace": traceback.format_exc()}


@app.get("/api/refresh/status")
def refresh_status():
    return _refresh_status


async def run_refresh(days_back: int = 14, keyword_filter: list = None):
    _refresh_status["running"] = True
    _refresh_status["progress"] = "Starting..."

    try:
        keywords = db.get_keywords(active_only=True)
        kw_list = [k["keyword"] for k in keywords]
        if keyword_filter:
            kw_list = [k for k in kw_list if k in keyword_filter]

        if not kw_list:
            _refresh_status["progress"] = "No keywords to search"
            _refresh_status["running"] = False
            return

        kw_video_map: dict = {}
        all_video_ids: set = set()

        for i, kw in enumerate(kw_list):
            _refresh_status["progress"] = f"Searching {i+1}/{len(kw_list)}: {kw}"
            ids = yt.search_videos(kw, days_back=days_back)
            kw_video_map[kw] = set(ids)
            all_video_ids.update(ids)

        _refresh_status["progress"] = f"Fetching details for {len(all_video_ids)} videos..."
        videos = yt.fetch_video_details(list(all_video_ids))

        for v in videos:
            matched = [kw for kw, ids in kw_video_map.items() if v["video_id"] in ids]
            if not matched:
                text = (v["title"] + " " + v.get("description", "")).lower()
                matched = [kw for kw in kw_list if kw.lower() in text]
            v["keywords_matched"] = matched

        _refresh_status["progress"] = f"Analyzing {len(videos)} videos..."
        videos_processed = 0
        breakouts_found = 0

        for v in videos:
            channel_id = v["channel_id"]
            try:
                ch_data = yt.get_channel_data(channel_id, v.get("channel_name", ""))
            except Exception as e:
                print(f"[Refresh] Channel error {channel_id}: {e}")
                ch_data = {"subscriber_count": 0, "avg_views": 0.0}

            score_data = ol.compute_outlier_score(
                v["view_count"],
                ch_data.get("subscriber_count", 0),
                ch_data.get("avg_views", 0.0),
                published_at=v.get("published_at"),
                like_count=v.get("like_count", 0),
                comment_count=v.get("comment_count", 0),
            )

            db.upsert_video(v)
            db.upsert_outlier_score(
                v["video_id"],
                score_data["view_to_sub_ratio"],
                score_data["view_to_average_ratio"],
                score_data["outlier_score"],
                score_data["is_breakout"],
            )

            videos_processed += 1
            if score_data["is_breakout"]:
                breakouts_found += 1
            _refresh_status["progress"] = f"Processing {videos_processed}/{len(videos)} videos..."

        _refresh_status["progress"] = f"Done — {breakouts_found} breakouts out of {videos_processed} videos"
        _refresh_status["last_done"] = datetime.utcnow().isoformat()

    except Exception as e:
        _refresh_status["progress"] = f"Error: {e}"
        print(f"[Refresh] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _refresh_status["running"] = False


# ── Saved Videos ───────────────────────────────────────────────────────────────

@app.get("/api/saved")
def list_saved():
    return db.get_saved_videos()


@app.post("/api/saved/{video_id}")
def save_video(video_id: str, body: SaveVideoRequest):
    v = db.get_video_detail(video_id)
    if not v:
        raise HTTPException(404, "Video not found in database. Refresh first.")
    db.save_video(video_id, body.notes or "")
    return {"ok": True}


@app.delete("/api/saved/{video_id}")
def unsave_video(video_id: str):
    db.unsave_video(video_id)
    return {"ok": True}


@app.patch("/api/saved/{video_id}/notes")
def update_notes(video_id: str, body: UpdateNotesRequest):
    db.update_video_notes(video_id, body.notes)
    return {"ok": True}


# ── Quota ──────────────────────────────────────────────────────────────────────

@app.get("/api/quota")
def get_quota():
    return db.get_quota_used()


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    return db.get_stats_summary()


# ── Trends ─────────────────────────────────────────────────────────────────────

@app.get("/api/trends/{keyword}")
def get_trend(keyword: str):
    return tr_mod.get_trend(keyword)


@app.get("/api/trends")
def get_all_trends():
    keywords = db.get_keywords(active_only=True)
    kw_list = [k["keyword"] for k in keywords]
    return tr_mod.get_trends_for_keywords(kw_list)


# ── TikTok Trends ─────────────────────────────────────────────────────────────

@app.get("/api/tiktok-trends")
def get_tiktok_trends():
    """Get cached TikTok trend data for all scanned keywords."""
    return db.get_all_tiktok_trends()


@app.get("/api/tiktok-trends/{keyword}")
def get_tiktok_trend(keyword: str):
    """Get TikTok trend data for a single keyword."""
    cached = db.get_cached_tiktok_trend(keyword)
    if cached:
        return cached
    result = tt.scan_niche_trends([keyword])
    return result.get(keyword, {"keyword": keyword, "available": False})


@app.post("/api/tiktok-trends/scan")
async def scan_tiktok_trends(background_tasks: BackgroundTasks):
    """Scan all active keywords for TikTok trends (background). Falls back OK on Vercel."""
    if _refresh_status["running"]:
        return {"ok": False, "message": "A scan is already running"}
    background_tasks.add_task(run_tiktok_scan)
    return {"ok": True, "message": "TikTok trend scan started"}


@app.post("/api/tiktok-trends/scan-keyword")
def scan_tiktok_keyword(keyword: str):
    """Synchronously scan a single keyword for TikTok trends. Works on Vercel."""
    try:
        result = tt.scan_niche_trends([keyword])
        data = result.get(keyword, {})
        return {"ok": True, "keyword": keyword, "data": data}
    except Exception as e:
        return {"ok": False, "keyword": keyword, "error": str(e)}


async def run_tiktok_scan():
    _refresh_status["running"] = True
    _refresh_status["progress"] = "Scanning TikTok trends..."
    try:
        keywords = db.get_keywords(active_only=True)
        kw_list = [k["keyword"] for k in keywords]
        total = len(kw_list)
        for i, kw in enumerate(kw_list):
            _refresh_status["progress"] = f"TikTok scan {i+1}/{total}: {kw}"
            tt.scan_niche_trends([kw])
        _refresh_status["progress"] = f"TikTok scan done — {total} keywords analyzed"
        _refresh_status["last_done"] = datetime.utcnow().isoformat()
    except Exception as e:
        _refresh_status["progress"] = f"Error: {e}"
        import traceback
        traceback.print_exc()
    finally:
        _refresh_status["running"] = False


# ── Tracked Channels ──────────────────────────────────────────────────────

@app.get("/api/channels")
def list_tracked_channels():
    return db.get_tracked_channels()


@app.post("/api/channels/track")
def track_channel(body: TrackChannelRequest):
    if not body.channel_id:
        raise HTTPException(400, "channel_id required")
    # Fetch fresh channel data if we don't have it
    try:
        ch_data = yt.get_channel_data(body.channel_id, body.channel_name)
    except Exception:
        ch_data = {"subscriber_count": 0, "avg_views": 0}
    db.track_channel(
        body.channel_id,
        body.channel_name or ch_data.get("channel_name", ""),
        ch_data.get("subscriber_count", 0),
        ch_data.get("avg_views", 0),
        body.why,
    )
    return {"ok": True}


@app.delete("/api/channels/{channel_id}")
def untrack_channel(channel_id: str):
    db.untrack_channel(channel_id)
    return {"ok": True}


@app.get("/api/channels/{channel_id}/is-tracked")
def check_tracked(channel_id: str):
    return {"tracked": db.is_channel_tracked(channel_id)}


@app.post("/api/channels/scan")
async def scan_channels(background_tasks: BackgroundTasks):
    """Scan all tracked channels for breakout videos."""
    if _refresh_status["running"]:
        return {"ok": False, "message": "Refresh already running"}
    background_tasks.add_task(run_channel_scan)
    return {"ok": True, "message": "Channel scan started"}


async def run_channel_scan():
    """Discover breakout videos from all tracked channels."""
    _refresh_status["running"] = True
    _refresh_status["progress"] = "Scanning tracked channels..."

    try:
        tracked = db.get_tracked_channels()
        if not tracked:
            _refresh_status["progress"] = "No tracked channels"
            _refresh_status["running"] = False
            return

        total_breakouts = 0
        total_videos = 0

        for i, ch in enumerate(tracked):
            channel_id = ch["channel_id"]
            _refresh_status["progress"] = f"Scanning channel {i+1}/{len(tracked)}: {ch['channel_name']}"

            # Fetch recent videos from this channel
            recent = yt.fetch_channel_recent_videos(channel_id, max_results=30)
            if not recent:
                continue

            # Get channel stats for scoring
            ch_data = yt.get_channel_data(channel_id, ch["channel_name"])
            sub_count = ch_data.get("subscriber_count", 0)
            avg_views = ch_data.get("avg_views", 0)

            # Fetch full details for these videos
            video_ids = [v["video_id"] for v in recent]
            videos = yt.fetch_video_details(video_ids)

            for v in videos:
                v["keywords_matched"] = [f"channel:{ch['channel_name']}"]

                score_data = ol.compute_outlier_score(
                    v["view_count"],
                    sub_count,
                    avg_views,
                    published_at=v.get("published_at"),
                    like_count=v.get("like_count", 0),
                    comment_count=v.get("comment_count", 0),
                )

                db.upsert_video(v)
                db.upsert_outlier_score(
                    v["video_id"],
                    score_data["view_to_sub_ratio"],
                    score_data["view_to_average_ratio"],
                    score_data["outlier_score"],
                    score_data["is_breakout"],
                )

                total_videos += 1
                if score_data["is_breakout"]:
                    total_breakouts += 1

            db.update_channel_scan_time(channel_id)

        _refresh_status["progress"] = f"Channel scan done — {total_breakouts} breakouts from {total_videos} videos across {len(tracked)} channels"
        _refresh_status["last_done"] = datetime.utcnow().isoformat()

    except Exception as e:
        _refresh_status["progress"] = f"Error: {e}"
        import traceback
        traceback.print_exc()
    finally:
        _refresh_status["running"] = False
