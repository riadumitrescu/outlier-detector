"""
Outlier detection scoring and packaging analysis.

Scoring factors:
  - view_to_sub_ratio:     views / subscriber count (how far beyond the audience)
  - view_to_average_ratio: views / channel average (how far above baseline)
  - velocity_score:        views per day, normalized (rewards fast-growing videos)
  - engagement_bonus:      like+comment rate above baseline (signals quality, not just clickbait)
"""

import re
from datetime import datetime, timezone

BREAKOUT_THRESHOLD_SCORE = 3.0


def compute_outlier_score(
    view_count: int,
    subscriber_count: int,
    channel_avg_views: float,
    published_at: str = None,
    like_count: int = 0,
    comment_count: int = 0,
) -> dict:
    # --- Core ratios ---
    if subscriber_count and subscriber_count > 0:
        view_to_sub_ratio = view_count / subscriber_count
    else:
        view_to_sub_ratio = 0.0

    if channel_avg_views and channel_avg_views > 0:
        view_to_average_ratio = view_count / channel_avg_views
    else:
        view_to_average_ratio = 0.0

    # --- Velocity: views per day since upload ---
    days_up = 1
    if published_at:
        try:
            pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            days_up = max((datetime.now(timezone.utc) - pub).days, 1)
        except Exception:
            pass
    views_per_day = view_count / days_up

    # Velocity score: reward videos gaining views quickly
    # A video getting 10K+/day from a small channel is exceptional
    if subscriber_count and subscriber_count > 0:
        velocity_score = min(views_per_day / max(subscriber_count * 0.1, 100), 10.0)
    else:
        velocity_score = min(views_per_day / 5000, 5.0)

    # --- Engagement bonus ---
    engagement_rate = 0.0
    if view_count > 0:
        engagement_rate = (like_count + comment_count) / view_count
    # Good engagement is ~4-8% like rate + comments. Bonus for above-average engagement.
    engagement_bonus = min(engagement_rate * 20, 2.0)  # caps at 2.0 for 10%+ engagement

    # --- Recency bonus: newer videos get a small boost ---
    if days_up <= 3:
        recency_bonus = 1.5
    elif days_up <= 7:
        recency_bonus = 1.0
    elif days_up <= 14:
        recency_bonus = 0.5
    else:
        recency_bonus = 0.0

    # --- Combined score ---
    # Weighted: channel outperformance (40%), sub reach (25%), velocity (20%), engagement (10%), recency (5%)
    outlier_score = (
        view_to_average_ratio * 0.40
        + view_to_sub_ratio * 0.25
        + velocity_score * 0.20
        + engagement_bonus * 0.10
        + recency_bonus * 0.05
    )

    is_breakout = (
        outlier_score >= BREAKOUT_THRESHOLD_SCORE
        or view_to_average_ratio >= 3.0
        or (view_to_sub_ratio >= 3.0 and velocity_score >= 1.0)
    )

    return {
        "view_to_sub_ratio": round(view_to_sub_ratio, 4),
        "view_to_average_ratio": round(view_to_average_ratio, 4),
        "velocity_score": round(velocity_score, 4),
        "engagement_bonus": round(engagement_bonus, 4),
        "views_per_day": round(views_per_day),
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

    # Detect niche video format (psych/self-improvement/cultural commentary)
    niche_format = detect_niche_format(title_lower, title)

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
        "niche_format": niche_format,
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


# ── Niche video format detection ────────────────────────────────────────────
# Detects which of the 5 content formats a video fits:
#   1. Identity hook — unusual personal experience as entry point
#   2. Psychological reframe — reframing common experience with research
#   3. "Things nobody tells you" — searchable, skill-adjacent, filtered through a lens
#   4. Cultural commentary — cross-cultural, slow, systemic observation
#   5. "Here's my actual system" — personal workflow/routine/setup

NICHE_FORMATS = [
    {
        "id": "identity_hook",
        "label": "Identity Hook",
        "description": "Personal experience as curiosity hook → universal insight",
        "color": "#8B5CF6",  # purple
        "patterns": [
            r"(?:i'?m|i am|being) (?:a |an )?(?:\w+ )?(?:who|that|and)",
            r"(?:i (?:grew up|was born|lived|moved|came from|speak|published|built|dropped))",
            r"(?:as (?:a|an) \w+)",
            r"(?:what it'?s like|what (?:being|living|growing))",
            r"(?:my life as|growing up (?:as|in|with|between))",
            r"(?:i'?ve (?:lived|been|traveled|spoken|moved).*\d)",
            r"(?:at (?:age )?\d+,? i)",
            r"(?:i (?:never|didn'?t|don'?t) (?:had|have|know|feel|fit))",
        ],
    },
    {
        "id": "psychological_reframe",
        "label": "Psychological Reframe",
        "description": "Reframing common experience using research or frameworks",
        "color": "#EC4899",  # pink
        "patterns": [
            r"(?:why (?:you(?:'re| are)?|we) (?:actually|really|aren'?t|don'?t|can'?t|shouldn'?t|feel))",
            r"(?:the (?:real|actual|true|hidden|surprising) (?:reason|cause|science|psychology))",
            r"(?:(?:is(?:n'?t)?|not) (?:what you think|about|actually|really))",
            r"(?:the (?:psychology|science|neuroscience|research) (?:of|behind|explains))",
            r"(?:(?:self[- ])?(?:compassion|sabotage|regulation|worth|esteem|discipline) (?:vs|versus|or|isn'?t))",
            r"(?:reframe|reframing|rethink|rethinking)",
            r"(?:(?:attachment|nervous system|dopamine|cortisol|trauma) (?:style|theory|response|explained))",
            r"(?:what \w+ (?:actually|really) (?:means|is|does|looks))",
        ],
    },
    {
        "id": "things_nobody_tells",
        "label": "Things Nobody Tells You",
        "description": "Searchable, skill-adjacent, filtered through personal lens",
        "color": "#F59E0B",  # amber
        "patterns": [
            r"(?:(?:things|what|stuff) (?:nobody|no one|people don'?t) (?:tells?|told|talk|mention))",
            r"(?:(?:honest|real|raw|brutal) (?:truth|talk|take|advice|guide) about)",
            r"(?:what i (?:wish|would|should) (?:i |have )?(?:knew|known|learned|told))",
            r"(?:the truth about|reality of|honest review)",
            r"(?:(?:\d+ )?(?:things|lessons|tips|rules|truths) (?:i learned|for|about|from))",
            r"(?:a (?:beginner'?s?|complete|honest|real) guide to)",
            r"(?:how to (?:actually|really) (?:start|learn|study|read|journal|meditate))",
            r"(?:what they don'?t (?:tell|teach|show|mention))",
        ],
    },
    {
        "id": "cultural_commentary",
        "label": "Cultural Commentary",
        "description": "Cross-cultural observation, systemic critique, slow commentary",
        "color": "#06B6D4",  # cyan
        "patterns": [
            r"(?:why (?:gen z|millennials|our generation|society|culture|we'?re|the world))",
            r"(?:the (?:problem|crisis|epidemic|myth|lie|trap) (?:of|with|behind|nobody))",
            r"(?:(?:hustle|productivity|wellness|self[- ]improvement|dating|social media) (?:culture|trap|myth|lie|toxic))",
            r"(?:(?:chronically|terminally) online|brain rot|main character|parasocial)",
            r"(?:(?:cross[- ]cultural|cultural|in \w+ vs|between (?:two|cultures)))",
            r"(?:(?:loneliness|isolation|disconnection|burnout) (?:epidemic|crisis|generation))",
            r"(?:why (?:everyone|nobody|people) (?:is|are|feels?))",
            r"(?:(?:quiet|soft|slow|analog|offline|intentional) (?:living|life|era|quitting))",
        ],
    },
    {
        "id": "my_system",
        "label": "My Actual System",
        "description": "Personal workflow, routine, or setup grounded in real life",
        "color": "#10B981",  # emerald
        "patterns": [
            r"(?:my (?:actual|real|exact|entire|full|complete|daily|weekly|morning|evening|night)?\s*(?:routine|system|method|process|setup|workflow|schedule|curriculum|protocol))",
            r"(?:how i (?:actually |really )?(?:organize|plan|study|journal|read|track|manage|review|structure))",
            r"(?:(?:weekly|daily|monthly|annual) (?:review|reset|planning|check-?in|routine))",
            r"(?:what'?s in my (?:bag|desk|setup|journal|planner|toolkit))",
            r"(?:(?:everything|all) i (?:use|do|track|carry|own) (?:in|for|to))",
            r"(?:i (?:tried|tested|used) (?:this|it) for (?:\d+ )?(?:days|weeks|months))",
            r"(?:(?:bag|desk|room|journal|planner|shelf) (?:tour|essentials|setup))",
        ],
    },
]


def detect_niche_format(title_lower: str, title_original: str = "") -> list[dict]:
    """
    Detect which niche content format(s) a video title matches.
    Returns a list of matched formats with confidence.
    """
    matches = []
    for fmt in NICHE_FORMATS:
        matched_patterns = 0
        for pattern in fmt["patterns"]:
            if re.search(pattern, title_lower):
                matched_patterns += 1

        if matched_patterns > 0:
            confidence = "strong" if matched_patterns >= 2 else "likely"
            matches.append({
                "id": fmt["id"],
                "label": fmt["label"],
                "description": fmt["description"],
                "color": fmt["color"],
                "confidence": confidence,
                "pattern_matches": matched_patterns,
            })

    # Sort by number of pattern matches (strongest match first)
    matches.sort(key=lambda x: -x["pattern_matches"])
    return matches
