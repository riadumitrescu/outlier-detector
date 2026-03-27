import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

import os as _os
if _os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/data.db")
else:
    DB_PATH = Path(__file__).parent / "data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                tags TEXT,
                category_id TEXT,
                published_at TEXT,
                duration TEXT,
                duration_seconds INTEGER,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                thumbnail_url TEXT,
                channel_id TEXT,
                channel_name TEXT,
                keywords_matched TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                subscriber_count INTEGER,
                avg_views REAL,
                last_video_titles TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS outlier_scores (
                video_id TEXT PRIMARY KEY,
                view_to_sub_ratio REAL,
                view_to_average_ratio REAL,
                outlier_score REAL,
                is_breakout INTEGER DEFAULT 0,
                calculated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS saved_videos (
                video_id TEXT PRIMARY KEY,
                notes TEXT DEFAULT '',
                saved_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quota_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                units_used INTEGER DEFAULT 0,
                last_refresh TEXT
            );

            CREATE TABLE IF NOT EXISTS trends_cache (
                keyword TEXT PRIMARY KEY,
                trend_data TEXT,
                direction TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tracked_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                subscriber_count INTEGER DEFAULT 0,
                avg_views REAL DEFAULT 0,
                why_tracked TEXT DEFAULT '',
                tracked_at TEXT DEFAULT (datetime('now')),
                last_scanned TEXT
            );

            CREATE TABLE IF NOT EXISTS tiktok_trends_cache (
                keyword TEXT PRIMARY KEY,
                suggestions TEXT,
                hashtag_views INTEGER,
                platform_comparison TEXT,
                opportunity_score TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Seed default keywords — aligned with psych/identity/cultural commentary niche
        defaults = [
            # Psychology / mental health (proven search volume)
            "self compassion vs self discipline", "attachment theory explained",
            "emotional regulation tips", "signs of burnout",
            "nervous system regulation", "shadow work for beginners",
            "overthinking", "mental health",
            # Language / identity (unique angle)
            "how I learned English", "language learning tips",
            "speaking multiple languages", "growing up bilingual",
            # Study / academic
            "weekly review system", "how to study effectively",
            "personal curriculum",
            # Intentional living / digital
            "digital minimalism", "phone addiction",
            "intentional living tips", "slow living",
            # Relationships / identity
            "relationships across cultures", "asexuality explained",
            # Journaling
            "journaling for beginners", "journaling prompts",
            "how to start journaling",
            # Cultural commentary
            "brain rot", "hustle culture", "self improvement trap",
            "loneliness epidemic", "parasocial relationships",
            "chronically online", "main character syndrome",
            # Trending / high-signal
            "somatic exercises", "nervous system reset",
            "emotional immaturity signs", "dopamine detox",
            "quiet quitting psychology",
        ]
        for kw in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (kw,)
            )
        conn.commit()


# ── Keywords ──────────────────────────────────────────────────────────────────

def get_keywords(active_only=True):
    with get_conn() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM keywords WHERE active=1 ORDER BY keyword"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM keywords ORDER BY keyword"
            ).fetchall()
        return [dict(r) for r in rows]


def add_keyword(keyword: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO keywords (keyword, active) VALUES (?, 1)",
            (keyword.lower().strip(),)
        )
        conn.execute(
            "UPDATE keywords SET active=1 WHERE keyword=?",
            (keyword.lower().strip(),)
        )
        conn.commit()


def remove_keyword(keyword: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE keywords SET active=0 WHERE keyword=?",
            (keyword.lower().strip(),)
        )
        conn.commit()


# ── Channels (24h cache) ───────────────────────────────────────────────────────

def get_cached_channel(channel_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM channels WHERE channel_id=?", (channel_id,)
        ).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if datetime.utcnow() - fetched > timedelta(hours=24):
            return None
        data = dict(row)
        if data.get("last_video_titles"):
            data["last_video_titles"] = json.loads(data["last_video_titles"])
        return data


def upsert_channel(channel_id, channel_name, subscriber_count, avg_views, last_video_titles):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO channels (channel_id, channel_name, subscriber_count, avg_views, last_video_titles, fetched_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_name=excluded.channel_name,
                subscriber_count=excluded.subscriber_count,
                avg_views=excluded.avg_views,
                last_video_titles=excluded.last_video_titles,
                fetched_at=excluded.fetched_at
        """, (channel_id, channel_name, subscriber_count, avg_views,
              json.dumps(last_video_titles)))
        conn.commit()


# ── Videos ─────────────────────────────────────────────────────────────────────

def get_cached_video(video_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE video_id=?", (video_id,)
        ).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if datetime.utcnow() - fetched > timedelta(hours=6):
            return None
        data = dict(row)
        if data.get("tags"):
            data["tags"] = json.loads(data["tags"])
        if data.get("keywords_matched"):
            data["keywords_matched"] = json.loads(data["keywords_matched"])
        return data


def upsert_video(v: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO videos (
                video_id, title, description, tags, category_id,
                published_at, duration, duration_seconds, view_count,
                like_count, comment_count, thumbnail_url,
                channel_id, channel_name, keywords_matched, fetched_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(video_id) DO UPDATE SET
                view_count=excluded.view_count,
                like_count=excluded.like_count,
                comment_count=excluded.comment_count,
                keywords_matched=excluded.keywords_matched,
                fetched_at=excluded.fetched_at
        """, (
            v["video_id"], v["title"], v.get("description", ""),
            json.dumps(v.get("tags", [])), v.get("category_id", ""),
            v["published_at"], v.get("duration", ""), v.get("duration_seconds", 0),
            v.get("view_count", 0), v.get("like_count", 0), v.get("comment_count", 0),
            v.get("thumbnail_url", ""), v["channel_id"], v.get("channel_name", ""),
            json.dumps(v.get("keywords_matched", []))
        ))
        conn.commit()


def upsert_outlier_score(video_id, vts_ratio, vta_ratio, score, is_breakout):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO outlier_scores (video_id, view_to_sub_ratio, view_to_average_ratio, outlier_score, is_breakout, calculated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(video_id) DO UPDATE SET
                view_to_sub_ratio=excluded.view_to_sub_ratio,
                view_to_average_ratio=excluded.view_to_average_ratio,
                outlier_score=excluded.outlier_score,
                is_breakout=excluded.is_breakout,
                calculated_at=excluded.calculated_at
        """, (video_id, vts_ratio, vta_ratio, score, 1 if is_breakout else 0))
        conn.commit()


# ── Saved Videos ──────────────────────────────────────────────────────────────

def save_video(video_id: str, notes: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO saved_videos (video_id, notes) VALUES (?, ?)
        """, (video_id, notes))
        conn.commit()


def unsave_video(video_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM saved_videos WHERE video_id=?", (video_id,))
        conn.commit()


def update_video_notes(video_id: str, notes: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE saved_videos SET notes=? WHERE video_id=?",
            (notes, video_id)
        )
        conn.commit()


def get_saved_videos():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT sv.video_id, sv.notes, sv.saved_at,
                   v.title, v.thumbnail_url, v.channel_name, v.channel_id,
                   v.view_count, v.like_count, v.comment_count,
                   v.published_at, v.duration_seconds, v.description, v.tags,
                   os.outlier_score, os.view_to_sub_ratio, os.view_to_average_ratio, os.is_breakout,
                   c.subscriber_count, c.avg_views
            FROM saved_videos sv
            LEFT JOIN videos v ON sv.video_id = v.video_id
            LEFT JOIN outlier_scores os ON sv.video_id = os.video_id
            LEFT JOIN channels c ON v.channel_id = c.channel_id
            ORDER BY sv.saved_at DESC
        """).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for field in ["tags"]:
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        d[field] = []
            result.append(d)
        return result


def is_saved(video_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM saved_videos WHERE video_id=?", (video_id,)
        ).fetchone()
        return row is not None


# ── Full result fetch with filtering ──────────────────────────────────────────

def _parse_json_fields(d: dict) -> dict:
    for field in ["tags", "keywords_matched"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = []
    return d


_VIDEO_SELECT = """
    SELECT v.*, os.outlier_score, os.view_to_sub_ratio, os.view_to_average_ratio, os.is_breakout,
           c.subscriber_count, c.avg_views,
           CASE WHEN sv.video_id IS NOT NULL THEN 1 ELSE 0 END as is_saved
    FROM videos v
    LEFT JOIN outlier_scores os ON v.video_id = os.video_id
    LEFT JOIN channels c ON v.channel_id = c.channel_id
    LEFT JOIN saved_videos sv ON v.video_id = sv.video_id
"""


def get_videos(
    limit: int = 50,
    keyword: str = None,
    breakout_only: bool = False,
    channel_tier: str = None,
    sort_by: str = "outlier_score",
    min_views: int = None,
    max_sub_count: int = None,
    min_sub_count: int = None,
):
    """Flexible video query with filtering and sorting."""
    where = []
    params = []

    if breakout_only:
        where.append("os.is_breakout = 1")

    if keyword:
        where.append("v.keywords_matched LIKE ?")
        params.append(f'%"{keyword}"%')

    if min_views:
        where.append("v.view_count >= ?")
        params.append(min_views)

    # Channel tier filtering by subscriber range
    tier_ranges = {
        "nano": (0, 999),
        "micro": (1000, 9999),
        "small": (10000, 99999),
        "medium": (100000, 999999),
        "large": (1000000, 999999999),
    }
    if channel_tier and channel_tier in tier_ranges:
        lo, hi = tier_ranges[channel_tier]
        where.append("c.subscriber_count BETWEEN ? AND ?")
        params.extend([lo, hi])

    if min_sub_count is not None:
        where.append("c.subscriber_count >= ?")
        params.append(min_sub_count)
    if max_sub_count is not None:
        where.append("c.subscriber_count <= ?")
        params.append(max_sub_count)

    where_clause = "WHERE " + " AND ".join(where) if where else ""

    sort_map = {
        "outlier_score": "os.outlier_score DESC",
        "views": "v.view_count DESC",
        "recent": "v.published_at DESC",
        "view_to_sub": "os.view_to_sub_ratio DESC",
        "view_to_avg": "os.view_to_average_ratio DESC",
        "likes": "v.like_count DESC",
        "comments": "v.comment_count DESC",
    }
    order = sort_map.get(sort_by, "os.outlier_score DESC")

    query = f"{_VIDEO_SELECT} {where_clause} ORDER BY {order} LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_parse_json_fields(dict(r)) for r in rows]


def get_breakout_videos(limit=50, keyword=None):
    return get_videos(limit=limit, keyword=keyword, breakout_only=True, min_views=10000)


def get_recent_videos(limit=50):
    return get_videos(limit=limit, sort_by="recent", min_views=10000)


def get_video_detail(video_id: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT v.*, os.outlier_score, os.view_to_sub_ratio, os.view_to_average_ratio, os.is_breakout,
                   c.subscriber_count, c.avg_views, c.last_video_titles,
                   CASE WHEN sv.video_id IS NOT NULL THEN 1 ELSE 0 END as is_saved,
                   sv.notes
            FROM videos v
            LEFT JOIN outlier_scores os ON v.video_id = os.video_id
            LEFT JOIN channels c ON v.channel_id = c.channel_id
            LEFT JOIN saved_videos sv ON v.video_id = sv.video_id
            WHERE v.video_id = ?
        """, (video_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for field in ["tags", "keywords_matched", "last_video_titles"]:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    d[field] = []
        return d


def get_keyword_breakout_summary():
    """Count breakout videos per keyword from the keywords_matched field."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.keywords_matched
            FROM videos v
            JOIN outlier_scores os ON v.video_id = os.video_id
            WHERE os.is_breakout = 1
        """).fetchall()
    counts = {}
    for row in rows:
        try:
            keywords = json.loads(row["keywords_matched"] or "[]")
        except Exception:
            keywords = []
        for kw in keywords:
            counts[kw] = counts.get(kw, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])


def get_stats_summary():
    """Dashboard-level stats."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM videos").fetchone()["c"]
        breakouts = conn.execute("SELECT COUNT(*) as c FROM outlier_scores WHERE is_breakout=1").fetchone()["c"]
        saved = conn.execute("SELECT COUNT(*) as c FROM saved_videos").fetchone()["c"]
        channels = conn.execute("SELECT COUNT(*) as c FROM channels").fetchone()["c"]
        avg_score = conn.execute("SELECT AVG(outlier_score) as a FROM outlier_scores WHERE is_breakout=1").fetchone()["a"]
        top_score = conn.execute("SELECT MAX(outlier_score) as m FROM outlier_scores").fetchone()["m"]
        return {
            "total_videos": total,
            "breakout_count": breakouts,
            "saved_count": saved,
            "channels_tracked": channels,
            "avg_breakout_score": round(avg_score, 2) if avg_score else 0,
            "top_score": round(top_score, 2) if top_score else 0,
        }


def export_videos_csv(breakout_only=True):
    """Generate CSV string of video data for export."""
    videos = get_videos(limit=500, breakout_only=breakout_only, sort_by="outlier_score")
    if not videos:
        return ""

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Video ID", "Title", "Channel", "Views", "Likes", "Comments",
        "Subscribers", "Outlier Score", "Views/Subs", "Views/Avg",
        "Published", "Duration (s)", "URL", "Keywords"
    ])
    for v in videos:
        writer.writerow([
            v.get("video_id", ""),
            v.get("title", ""),
            v.get("channel_name", ""),
            v.get("view_count", 0),
            v.get("like_count", 0),
            v.get("comment_count", 0),
            v.get("subscriber_count", 0),
            v.get("outlier_score", 0),
            v.get("view_to_sub_ratio", 0),
            v.get("view_to_average_ratio", 0),
            v.get("published_at", ""),
            v.get("duration_seconds", 0),
            f"https://youtube.com/watch?v={v.get('video_id', '')}",
            ", ".join(v.get("keywords_matched", [])),
        ])
    return output.getvalue()


# ── Tracked Channels ─────────────────────────────────────────────────────

def get_tracked_channels():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT tc.*, c.subscriber_count as current_subs, c.avg_views as current_avg
            FROM tracked_channels tc
            LEFT JOIN channels c ON tc.channel_id = c.channel_id
            ORDER BY tc.tracked_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def track_channel(channel_id: str, channel_name: str, subscriber_count: int = 0, avg_views: float = 0, why: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO tracked_channels (channel_id, channel_name, subscriber_count, avg_views, why_tracked)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_name=excluded.channel_name,
                subscriber_count=excluded.subscriber_count,
                avg_views=excluded.avg_views,
                why_tracked=CASE WHEN excluded.why_tracked != '' THEN excluded.why_tracked ELSE tracked_channels.why_tracked END
        """, (channel_id, channel_name, subscriber_count, avg_views, why))
        conn.commit()


def untrack_channel(channel_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM tracked_channels WHERE channel_id=?", (channel_id,))
        conn.commit()


def is_channel_tracked(channel_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM tracked_channels WHERE channel_id=?", (channel_id,)).fetchone()
        return row is not None


def update_channel_scan_time(channel_id: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tracked_channels SET last_scanned=datetime('now') WHERE channel_id=?",
            (channel_id,)
        )
        conn.commit()


# ── Quota Tracking ────────────────────────────────────────────────────────────

def log_quota(units: int):
    today = datetime.utcnow().date().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM quota_log WHERE date=?", (today,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE quota_log SET units_used=units_used+?, last_refresh=datetime('now') WHERE date=?",
                (units, today)
            )
        else:
            conn.execute(
                "INSERT INTO quota_log (date, units_used, last_refresh) VALUES (?, ?, datetime('now'))",
                (today, units)
            )
        conn.commit()


def get_quota_used():
    today = datetime.utcnow().date().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT units_used, last_refresh FROM quota_log WHERE date=?", (today,)
        ).fetchone()
        if row:
            return {"units_used": row["units_used"], "last_refresh": row["last_refresh"], "limit": 10000}
        return {"units_used": 0, "last_refresh": None, "limit": 10000}


# ── Trends Cache ──────────────────────────────────────────────────────────────

def get_cached_trend(keyword: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM trends_cache WHERE keyword=?", (keyword,)
        ).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if datetime.utcnow() - fetched > timedelta(hours=12):
            return None
        data = dict(row)
        if data.get("trend_data"):
            try:
                data["trend_data"] = json.loads(data["trend_data"])
            except Exception:
                pass
        return data


def upsert_trend(keyword: str, trend_data: list, direction: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO trends_cache (keyword, trend_data, direction, fetched_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(keyword) DO UPDATE SET
                trend_data=excluded.trend_data,
                direction=excluded.direction,
                fetched_at=excluded.fetched_at
        """, (keyword, json.dumps(trend_data), direction))
        conn.commit()


# ── TikTok Trends Cache ──────────────────────────────────────────────────────

def get_cached_tiktok_trend(keyword: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tiktok_trends_cache WHERE keyword=?", (keyword,)
        ).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if datetime.utcnow() - fetched > timedelta(hours=6):
            return None
        data = dict(row)
        for field in ["suggestions", "platform_comparison", "opportunity_score"]:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    pass
        return data


def upsert_tiktok_trend(keyword: str, result: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO tiktok_trends_cache (keyword, suggestions, hashtag_views, platform_comparison, opportunity_score, fetched_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(keyword) DO UPDATE SET
                suggestions=excluded.suggestions,
                hashtag_views=excluded.hashtag_views,
                platform_comparison=excluded.platform_comparison,
                opportunity_score=excluded.opportunity_score,
                fetched_at=excluded.fetched_at
        """, (
            keyword,
            json.dumps(result.get("suggestions", [])),
            result.get("hashtag_views"),
            json.dumps(result.get("platform_comparison", {})),
            json.dumps(result.get("opportunity_score", {})),
        ))
        conn.commit()


def get_all_tiktok_trends():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tiktok_trends_cache ORDER BY fetched_at DESC"
        ).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            for field in ["suggestions", "platform_comparison", "opportunity_score"]:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except Exception:
                        pass
            results.append(data)
        return results
