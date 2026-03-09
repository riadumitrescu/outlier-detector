"""
Outlier detection scoring and packaging analysis.
"""

import re

BREAKOUT_THRESHOLD_RATIO = 3.0
BREAKOUT_THRESHOLD_SCORE = 3.0


def compute_outlier_score(
    view_count: int,
    subscriber_count: int,
    channel_avg_views: float,
) -> dict:
    if subscriber_count and subscriber_count > 0:
        view_to_sub_ratio = view_count / subscriber_count
    else:
        view_to_sub_ratio = 0.0

    if channel_avg_views and channel_avg_views > 0:
        view_to_average_ratio = view_count / channel_avg_views
    else:
        view_to_average_ratio = 0.0

    outlier_score = (view_to_sub_ratio * 0.4) + (view_to_average_ratio * 0.6)

    is_breakout = (
        view_to_sub_ratio >= BREAKOUT_THRESHOLD_RATIO
        or view_to_average_ratio >= BREAKOUT_THRESHOLD_RATIO
        or outlier_score >= BREAKOUT_THRESHOLD_SCORE
    )

    return {
        "view_to_sub_ratio": round(view_to_sub_ratio, 4),
        "view_to_average_ratio": round(view_to_average_ratio, 4),
        "outlier_score": round(outlier_score, 4),
        "is_breakout": is_breakout,
    }


def get_channel_tier(subscriber_count: int) -> str:
    """Categorize channel by subscriber count."""
    if not subscriber_count or subscriber_count <= 0:
        return "unknown"
    if subscriber_count < 1_000:
        return "nano"          # < 1K
    if subscriber_count < 10_000:
        return "micro"         # 1K-10K
    if subscriber_count < 100_000:
        return "small"         # 10K-100K
    if subscriber_count < 1_000_000:
        return "medium"        # 100K-1M
    return "large"             # 1M+


CHANNEL_TIER_LABELS = {
    "nano": "< 1K",
    "micro": "1K–10K",
    "small": "10K–100K",
    "medium": "100K–1M",
    "large": "1M+",
    "unknown": "Unknown",
}


# ── Title analysis ────────────────────────────────────────────────────────────

POWER_WORDS = {
    "secret", "shocking", "proven", "ultimate", "instant", "effortless",
    "dangerous", "powerful", "essential", "massive", "simple", "easy",
    "fastest", "biggest", "best", "worst", "never", "always", "only",
    "free", "new", "now", "today", "finally", "truth", "real", "honest",
    "hidden", "revealed", "exposed", "unlimited", "guaranteed", "incredible",
    "unbelievable", "life-changing", "game-changing", "exact",
    "transformative", "surprising", "unexpected", "viral", "trending",
    "controversial", "brutal", "raw", "unfiltered", "authentic", "perfect",
    "complete", "definitive", "critical", "urgent", "warning", "stop",
    "hack", "hacks", "trick", "tricks", "mistake", "mistakes",
}

EMOTIONAL_TRIGGERS = {
    "anxiety", "fear", "stress", "overwhelm", "burnout", "depression",
    "loneliness", "regret", "shame", "guilt", "anger", "frustration",
    "hope", "joy", "love", "success", "freedom", "peace", "happiness",
    "confidence", "clarity", "purpose", "meaning", "growth", "change",
    "struggle", "pain", "healing", "recovery", "transformation",
    "motivation", "discipline", "failure", "lost", "broken", "stuck",
    "anxious", "overwhelmed", "exhausted", "inspired", "grateful",
    "lonely", "afraid", "sad", "happy", "proud", "calm", "focused",
}

# Common title formulas/patterns in self-improvement YouTube
TITLE_PATTERNS = [
    ("how_to", r"^how (?:to|i)", "How-to / Tutorial"),
    ("listicle", r"\d+\s+(?:ways|things|habits|tips|steps|rules|signs|reasons|lessons|mistakes|secrets|tools|books|hacks|tricks|principles)", "Listicle"),
    ("personal_story", r"(?:how i|i (?:spent|tried|quit|stopped|started|changed|learned|discovered))", "Personal Story"),
    ("challenge", r"(?:i (?:tried|did|lived|spent).*(?:\d+ days|\d+ hours|for a (?:week|month|year)))", "Challenge/Experiment"),
    ("warning", r"(?:stop|don'?t|never|quit|avoid|warning)", "Warning / Negative"),
    ("curiosity_gap", r"(?:why you|the (?:real |true )?reason|what nobody|no one tells)", "Curiosity Gap"),
    ("transformation", r"(?:changed my life|ruined my|saved my|transformed|before and after)", "Transformation"),
    ("versus", r"\bvs\.?\b", "Comparison"),
    ("this_is_why", r"(?:this is (?:why|how)|here'?s (?:why|how|what))", "Explainer"),
    ("after_x", r"(?:after \d+|what happened|what i learned)", "After X / Results"),
]


def analyze_title(title: str) -> dict:
    words = re.findall(r"\b\w+\b", title.lower())
    word_set = set(words)

    found_power = sorted(word_set & POWER_WORDS)
    found_emotional = sorted(word_set & EMOTIONAL_TRIGGERS)

    numbers = re.findall(r"\d+", title)
    has_number = len(numbers) > 0

    is_question = title.strip().endswith("?")
    has_parenthetical = bool(re.search(r"[\(\[].*?[\)\]]", title))
    has_colon = ":" in title
    has_pipe = "|" in title
    has_dash = " - " in title or " — " in title
    has_ellipsis = "..." in title or "…" in title
    starts_with_number = bool(re.match(r"^\d", title.strip()))
    all_caps_words = [w for w in title.split() if w.isupper() and len(w) > 1]

    char_count = len(title)

    # Detect title formula patterns
    title_lower = title.lower()
    detected_patterns = []
    for pattern_id, pattern_re, pattern_label in TITLE_PATTERNS:
        if re.search(pattern_re, title_lower):
            detected_patterns.append({"id": pattern_id, "label": pattern_label})

    # Title structure analysis
    if has_colon:
        structure = "two-part (colon)"
    elif has_pipe:
        structure = "two-part (pipe)"
    elif has_dash:
        structure = "two-part (dash)"
    elif has_parenthetical:
        structure = "main + qualifier"
    else:
        structure = "single statement"

    # Strength assessment
    strength_score = 0
    strength_notes = []
    if found_power:
        strength_score += 2
        strength_notes.append(f"{len(found_power)} power word(s)")
    if found_emotional:
        strength_score += 2
        strength_notes.append(f"{len(found_emotional)} emotional trigger(s)")
    if has_number:
        strength_score += 1
        strength_notes.append("contains number (specificity)")
    if is_question:
        strength_score += 1
        strength_notes.append("question format (curiosity)")
    if has_parenthetical:
        strength_score += 1
        strength_notes.append("parenthetical qualifier")
    if detected_patterns:
        strength_score += 1
        strength_notes.append(f"matches {detected_patterns[0]['label']} formula")
    if 40 <= char_count <= 65:
        strength_score += 1
        strength_notes.append("optimal length")
    elif char_count > 80:
        strength_notes.append("title may be too long")

    if strength_score >= 6:
        strength_label = "very strong"
    elif strength_score >= 4:
        strength_label = "strong"
    elif strength_score >= 2:
        strength_label = "moderate"
    else:
        strength_label = "weak"

    return {
        "char_count": char_count,
        "word_count": len(words),
        "power_words": found_power,
        "emotional_triggers": found_emotional,
        "numbers": numbers,
        "has_number": has_number,
        "starts_with_number": starts_with_number,
        "is_question": is_question,
        "has_parenthetical": has_parenthetical,
        "has_colon": has_colon,
        "has_pipe": has_pipe,
        "has_ellipsis": has_ellipsis,
        "all_caps_words": all_caps_words,
        "format": "question" if is_question else "statement",
        "structure": structure,
        "detected_patterns": detected_patterns,
        "strength": {
            "score": strength_score,
            "max": 8,
            "label": strength_label,
            "notes": strength_notes,
        },
    }


# ── Description analysis ─────────────────────────────────────────────────────

def analyze_description(description: str) -> dict:
    """Analyze video description for key elements."""
    if not description:
        return {"has_links": False, "has_timestamps": False, "has_cta": False, "word_count": 0}

    lines = description.strip().split("\n")
    word_count = len(description.split())

    # Timestamps (e.g., 0:00, 1:23, 12:34:56)
    timestamps = re.findall(r"\d{1,2}:\d{2}(?::\d{2})?", description)
    has_timestamps = len(timestamps) > 0

    # Links
    links = re.findall(r"https?://\S+", description)
    has_links = len(links) > 0

    # CTAs (calls to action)
    cta_patterns = [
        r"subscribe", r"like (?:this|the) video", r"comment below",
        r"check out", r"link (?:in|below)", r"follow me", r"join",
        r"sign up", r"download", r"free", r"newsletter",
    ]
    ctas_found = []
    desc_lower = description.lower()
    for p in cta_patterns:
        if re.search(p, desc_lower):
            ctas_found.append(p.replace(r"(?:this|the) ", "").replace(r"(?:in|below)", "in..."))

    # First line (often the hook)
    first_line = lines[0].strip() if lines else ""

    return {
        "word_count": word_count,
        "line_count": len(lines),
        "has_links": has_links,
        "link_count": len(links),
        "has_timestamps": has_timestamps,
        "timestamp_count": len(timestamps),
        "timestamps": timestamps[:20],
        "has_cta": len(ctas_found) > 0,
        "ctas": ctas_found,
        "first_line": first_line,
    }
