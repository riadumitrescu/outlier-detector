"""
Transcript fetching using youtube-transcript-api v1.x.
"""

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

_EMPTY = {
    "available": False,
    "full_text": "",
    "hook_text": "",
    "word_count": 0,
    "segments": [],
    "chapters": [],
    "retention_markers": [],
}


def get_transcript(video_id: str) -> dict:
    """
    Fetch transcript for a video. Returns rich analysis dict.
    Uses youtube-transcript-api v1.x instance API.
    """
    try:
        api = YouTubeTranscriptApi()

        # Try direct English fetch first (cheapest path)
        fetched = None
        try:
            fetched = api.fetch(video_id, languages=("en",))
        except Exception:
            pass

        # Fallback: list transcripts and pick the best one
        if fetched is None:
            try:
                transcript_list = api.list(video_id)
                # Try manually created English
                try:
                    t = transcript_list.find_manually_created_transcript(["en"])
                    fetched = t.fetch()
                except Exception:
                    pass
                # Try auto-generated English
                if fetched is None:
                    try:
                        t = transcript_list.find_generated_transcript(["en"])
                        fetched = t.fetch()
                    except Exception:
                        pass
                # Try any available transcript
                if fetched is None:
                    try:
                        t = transcript_list.find_transcript(["en", "en-US", "en-GB"])
                        fetched = t.fetch()
                    except Exception:
                        pass
            except Exception:
                pass

        if fetched is None:
            return {**_EMPTY, "error": "No transcript found"}

        # Convert to raw data (list of dicts) for consistent processing
        raw = fetched.to_raw_data()
        segments = [
            {"text": s["text"], "start": s["start"], "duration": s["duration"]}
            for s in raw
        ]

        full_text = " ".join(s["text"] for s in segments)
        word_count = len(full_text.split())

        # Hook = first 60 seconds
        hook_segments = [s for s in segments if s["start"] <= 60]
        hook_text = " ".join(s["text"] for s in hook_segments)

        # Extended hook = first 30 seconds (the critical opening)
        opening_segments = [s for s in segments if s["start"] <= 30]
        opening_text = " ".join(s["text"] for s in opening_segments)

        # Chapters detection
        chapters = _detect_chapters(segments)

        # Retention markers — find topic shifts and engagement hooks throughout
        retention_markers = _find_retention_markers(segments)

        # Word frequency for topic analysis (excluding stop words)
        topic_words = _extract_topic_words(full_text)

        return {
            "available": True,
            "error": None,
            "full_text": full_text,
            "hook_text": hook_text,
            "opening_text": opening_text,
            "word_count": word_count,
            "segments": segments,
            "chapters": chapters,
            "retention_markers": retention_markers,
            "topic_words": topic_words,
            "estimated_read_time_min": round(word_count / 150, 1),
        }

    except TranscriptsDisabled:
        return {**_EMPTY, "error": "Transcripts are disabled for this video"}
    except NoTranscriptFound:
        return {**_EMPTY, "error": "No transcript found for this video"}
    except Exception as e:
        return {**_EMPTY, "error": str(e)}


def _detect_chapters(segments: list) -> list:
    """Detect likely chapter/section breaks from transcript cadence."""
    chapters = []
    for seg in segments:
        text = seg["text"].strip()
        words = text.split()
        if not words or len(words) > 8:
            continue
        # Heuristic: short text that looks like a title/heading
        is_heading = (
            text.isupper()
            or text.endswith(":")
            or (len(words) <= 5 and text[0].isupper()
                and all(w[0].isupper() for w in words if len(w) > 2))
        )
        if is_heading:
            chapters.append({
                "text": text,
                "start": round(seg["start"], 1),
                "timestamp": _format_timestamp(seg["start"]),
            })
    return chapters[:25]


def _find_retention_markers(segments: list) -> list:
    """Find phrases that signal topic shifts or engagement hooks."""
    markers = []
    hook_phrases = [
        "but here's the thing", "here's what", "the truth is",
        "what i found", "the problem is", "let me explain",
        "most people don't", "nobody talks about", "the secret",
        "but wait", "here's why", "the real reason",
        "what if i told you", "pay attention", "this is important",
        "number one", "number two", "number three",
        "first", "second", "third", "finally",
        "step one", "step two", "step three",
        "the biggest mistake", "stop doing this",
    ]
    for seg in segments:
        text_lower = seg["text"].lower().strip()
        for phrase in hook_phrases:
            if phrase in text_lower:
                markers.append({
                    "text": seg["text"].strip(),
                    "phrase": phrase,
                    "start": round(seg["start"], 1),
                    "timestamp": _format_timestamp(seg["start"]),
                })
                break
    return markers[:30]


def _extract_topic_words(text: str, top_n: int = 20) -> list:
    """Extract top topic words from transcript (excluding stop words)."""
    import re
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "its", "this", "that", "was",
        "are", "were", "be", "been", "being", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "may", "might",
        "not", "no", "so", "if", "then", "than", "too", "very", "can",
        "just", "don", "now", "i", "you", "he", "she", "we", "they", "me",
        "my", "your", "our", "their", "what", "which", "who", "when",
        "where", "why", "how", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "only", "own", "same",
        "about", "up", "out", "like", "going", "get", "got", "go",
        "know", "think", "thing", "things", "really", "right", "because",
        "there", "here", "also", "well", "back", "even", "want", "way",
        "look", "make", "one", "two", "much", "kind", "them", "into",
        "over", "after", "before", "through", "these", "those", "um",
        "uh", "yeah", "okay", "oh", "something", "actually", "people",
        "gonna", "lot", "say", "said", "see", "come", "take",
    }
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    freq = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])[:top_n]
    return [{"word": w, "count": c} for w, c in sorted_words]


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
