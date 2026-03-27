"""
TikTok trend discovery module.

Scrapes TikTok for trending topics in your niche keywords, then cross-references
with YouTube search volume to find the 4-8 week lag opportunity window.

Methods:
  1. TikTok search suggestions API (public, no auth needed)
  2. TikTok hashtag view counts via embed endpoints
  3. Google Trends comparison (TikTok topic vs YouTube topic)
"""

import time
import json
import re
from datetime import datetime, timedelta
from typing import Optional

import database as db

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    try:
        import requests as httpx
        HTTPX_AVAILABLE = True
    except ImportError:
        HTTPX_AVAILABLE = False

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


# ── TikTok search suggestions ────────────────────────────────────────────────

TIKTOK_SUGGEST_URL = "https://www.tiktok.com/api/search/suggest/query/"
TIKTOK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.tiktok.com/",
}


def get_tiktok_suggestions(keyword: str) -> list[str]:
    """Get TikTok search autocomplete suggestions for a keyword."""
    if not HTTPX_AVAILABLE:
        return []
    try:
        params = {"keyword": keyword, "count": 10}
        if hasattr(httpx, 'Client'):
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                r = client.get(TIKTOK_SUGGEST_URL, params=params, headers=TIKTOK_HEADERS)
        else:
            r = httpx.get(TIKTOK_SUGGEST_URL, params=params, headers=TIKTOK_HEADERS, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json() if hasattr(r, 'json') and callable(r.json) else json.loads(r.text)
        suggestions = []
        for item in data.get("sug_list", data.get("data", [])):
            content = item.get("content", item.get("keyword", ""))
            if content:
                suggestions.append(content)
        return suggestions
    except Exception as e:
        print(f"[TikTok] Suggestion error for '{keyword}': {e}")
        return []


# ── TikTok hashtag stats ─────────────────────────────────────────────────────

def get_tiktok_hashtag_views(hashtag: str) -> Optional[int]:
    """
    Try to get view count for a TikTok hashtag.
    Uses TikTok's public challenge/hashtag endpoint.
    """
    if not HTTPX_AVAILABLE:
        return None
    try:
        clean = hashtag.replace("#", "").replace(" ", "").lower()
        url = f"https://www.tiktok.com/tag/{clean}"
        headers = {**TIKTOK_HEADERS}

        if hasattr(httpx, 'Client'):
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                r = client.get(url, headers=headers)
        else:
            r = httpx.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            return None

        # Extract view count from page HTML meta or JSON-LD
        text = r.text
        # Look for view count in various formats
        patterns = [
            r'"viewCount"\s*:\s*(\d+)',
            r'"stats"\s*:\s*\{[^}]*"videoCount"\s*:\s*(\d+)',
            r'(\d+(?:\.\d+)?[KMBkmb]?)\s*(?:views|videos)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                val = match.group(1)
                return _parse_count(val)
        return None
    except Exception as e:
        print(f"[TikTok] Hashtag error for '{hashtag}': {e}")
        return None


def _parse_count(val: str) -> int:
    """Parse counts like '1.2M', '500K', '3B' or plain integers."""
    val = val.strip()
    try:
        return int(val)
    except ValueError:
        pass
    multipliers = {'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000}
    if val and val[-1].lower() in multipliers:
        try:
            return int(float(val[:-1]) * multipliers[val[-1].lower()])
        except ValueError:
            pass
    return 0


# ── Cross-platform trend comparison ──────────────────────────────────────────

def compare_platform_trends(keyword: str) -> dict:
    """
    Compare a keyword's trend on TikTok vs YouTube using Google Trends.
    This identifies the TikTok→YouTube lag window.
    """
    if not PYTRENDS_AVAILABLE:
        return {
            "keyword": keyword,
            "available": False,
            "error": "pytrends not installed",
        }

    try:
        pytrends = TrendReq(hl="en-US", tz=360)

        # Get YouTube search trends
        pytrends.build_payload([keyword], timeframe="today 3-m", geo="", gprop="youtube")
        time.sleep(1)
        yt_df = pytrends.interest_over_time()

        # Get general web trends (proxy for TikTok since Google Trends
        # doesn't have a TikTok filter, but web trends capture TikTok spillover)
        pytrends.build_payload([keyword], timeframe="today 3-m", geo="", gprop="")
        time.sleep(1)
        web_df = pytrends.interest_over_time()

        yt_data = []
        web_data = []
        yt_direction = "stable"
        web_direction = "stable"

        if not yt_df.empty and keyword in yt_df.columns:
            yt_values = yt_df[keyword].tolist()
            yt_dates = [str(d.date()) for d in yt_df.index]
            yt_data = [{"date": d, "value": v} for d, v in zip(yt_dates, yt_values)]
            yt_direction = _calc_direction(yt_values)

        if not web_df.empty and keyword in web_df.columns:
            web_values = web_df[keyword].tolist()
            web_dates = [str(d.date()) for d in web_df.index]
            web_data = [{"date": d, "value": v} for d, v in zip(web_dates, web_values)]
            web_direction = _calc_direction(web_values)

        # Detect lag opportunity: web/TikTok rising but YouTube hasn't caught up
        lag_opportunity = (
            web_direction == "rising" and yt_direction in ("stable", "declining")
        )

        return {
            "keyword": keyword,
            "available": True,
            "youtube": {"data": yt_data, "direction": yt_direction},
            "web": {"data": web_data, "direction": web_direction},
            "lag_opportunity": lag_opportunity,
            "signal": _get_signal_label(web_direction, yt_direction),
        }

    except Exception as e:
        print(f"[TikTok Trends] Error for '{keyword}': {e}")
        return {
            "keyword": keyword,
            "available": False,
            "error": str(e),
        }


def _calc_direction(values: list) -> str:
    if len(values) < 8:
        return "stable"
    recent = sum(values[-4:]) / 4
    older = sum(values[-8:-4]) / 4
    if older == 0:
        return "rising" if recent > 0 else "stable"
    if recent > older * 1.15:
        return "rising"
    if recent < older * 0.85:
        return "declining"
    return "stable"


def _get_signal_label(web_dir: str, yt_dir: str) -> str:
    """Human-readable signal for content opportunity."""
    if web_dir == "rising" and yt_dir in ("stable", "declining"):
        return "JUMP ON THIS — trending on web/TikTok, YouTube hasn't caught up yet"
    if web_dir == "rising" and yt_dir == "rising":
        return "Hot topic — rising everywhere, make it now before saturation"
    if web_dir == "stable" and yt_dir == "rising":
        return "YouTube native trend — good for search, organic discovery"
    if web_dir == "declining" and yt_dir == "rising":
        return "Late YouTube wave — still has legs but peak may have passed"
    if web_dir == "declining" and yt_dir == "declining":
        return "Cooling off — evergreen angle needed to stand out"
    return "Stable — consistent search volume, good for evergreen content"


# ── Full niche trend scan ─────────────────────────────────────────────────────

def scan_niche_trends(keywords: list[str]) -> dict:
    """
    Scan a list of niche keywords for TikTok trends.
    Returns suggestions, hashtag data, and cross-platform comparison.
    """
    results = {}

    for kw in keywords:
        # Check cache first
        cached = db.get_cached_tiktok_trend(kw)
        if cached:
            results[kw] = cached
            continue

        result = {
            "keyword": kw,
            "suggestions": get_tiktok_suggestions(kw),
            "hashtag_views": get_tiktok_hashtag_views(kw),
            "platform_comparison": compare_platform_trends(kw),
            "fetched_at": datetime.utcnow().isoformat(),
        }

        # Compute opportunity score
        result["opportunity_score"] = _compute_opportunity_score(result)

        # Cache it
        db.upsert_tiktok_trend(kw, result)
        results[kw] = result

        time.sleep(1.5)  # rate limiting

    return results


def _compute_opportunity_score(result: dict) -> dict:
    """
    Score the content opportunity from 0-10.
    Factors: lag window, suggestion volume, hashtag popularity.
    """
    score = 0
    reasons = []

    # Platform comparison signals
    pc = result.get("platform_comparison", {})
    if pc.get("lag_opportunity"):
        score += 4
        reasons.append("TikTok→YouTube lag window detected")
    elif pc.get("youtube", {}).get("direction") == "rising":
        score += 2
        reasons.append("Rising on YouTube")

    web_dir = pc.get("web", {}).get("direction", "")
    if web_dir == "rising":
        score += 2
        reasons.append("Rising on web/TikTok")
    elif web_dir == "stable":
        score += 1
        reasons.append("Stable web interest")

    # Suggestion volume (more suggestions = more search activity)
    suggestions = result.get("suggestions", [])
    if len(suggestions) >= 8:
        score += 2
        reasons.append(f"{len(suggestions)} related searches on TikTok")
    elif len(suggestions) >= 4:
        score += 1
        reasons.append(f"{len(suggestions)} related searches on TikTok")

    # Hashtag popularity
    views = result.get("hashtag_views")
    if views and views > 1_000_000_000:
        score += 2
        reasons.append(f"Massive hashtag ({_format_count(views)} views)")
    elif views and views > 100_000_000:
        score += 1
        reasons.append(f"Popular hashtag ({_format_count(views)} views)")

    label = "skip"
    if score >= 7:
        label = "make it NOW"
    elif score >= 5:
        label = "strong opportunity"
    elif score >= 3:
        label = "worth considering"
    elif score >= 1:
        label = "low priority"

    return {
        "score": min(score, 10),
        "max": 10,
        "label": label,
        "reasons": reasons,
    }


def _format_count(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
