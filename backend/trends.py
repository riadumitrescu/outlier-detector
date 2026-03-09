"""
Google Trends integration using pytrends.
"""

import time
import database as db

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


def get_trend(keyword: str) -> dict:
    """
    Returns trend data for a keyword with 12h cache.
    direction: "rising", "stable", "declining"
    """
    cached = db.get_cached_trend(keyword)
    if cached:
        return cached

    if not PYTRENDS_AVAILABLE:
        return {"keyword": keyword, "trend_data": [], "direction": "unknown", "available": False}

    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        pytrends.build_payload([keyword], timeframe="today 3-m", geo="")
        time.sleep(1)  # be polite to Google
        df = pytrends.interest_over_time()

        if df.empty or keyword not in df.columns:
            return {"keyword": keyword, "trend_data": [], "direction": "stable", "available": True}

        values = df[keyword].tolist()
        dates = [str(d.date()) for d in df.index]

        trend_data = [{"date": d, "value": v} for d, v in zip(dates, values)]

        # Calculate direction based on last 4 weeks vs previous 4 weeks
        if len(values) >= 8:
            recent = sum(values[-4:]) / 4
            older = sum(values[-8:-4]) / 4
            if recent > older * 1.15:
                direction = "rising"
            elif recent < older * 0.85:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "stable"

        db.upsert_trend(keyword, trend_data, direction)

        return {
            "keyword": keyword,
            "trend_data": trend_data,
            "direction": direction,
            "available": True,
        }

    except Exception as e:
        print(f"[Trends] Error for '{keyword}': {e}")
        return {"keyword": keyword, "trend_data": [], "direction": "unknown", "available": False, "error": str(e)}


def get_trends_for_keywords(keywords: list[str]) -> dict:
    """Fetch trends for multiple keywords with rate limiting."""
    results = {}
    for kw in keywords:
        results[kw] = get_trend(kw)
        time.sleep(0.5)
    return results
