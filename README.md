# Outlier Detector

A personal YouTube research tool for content creators. Finds breakout videos in your niche — videos massively overperforming relative to their channel's size — and helps you reverse-engineer what's working.

## Quick Start

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

Open **http://localhost:5173** and click **Refresh** to start.

## First-Time Setup

If the `venv` doesn't exist yet:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

API keys are in `backend/.env` (gitignored).

## Features

### Outlier Detection Engine
- Searches YouTube for 20 tracked keywords (configurable)
- Calculates outlier score: `(views/subs * 0.4) + (views/channel_avg * 0.6)`
- Flags breakout videos (score >= 3, views/subs >= 3x, or views/avg >= 3x)
- Filters out Shorts (< 2 min) from results and from channel averages
- Caches channels (24h) and videos (6h) to save API quota

### Video Deep Dive
- **Title analysis**: power words, emotional triggers, detected formulas (listicle, how-to, curiosity gap, etc.), title strength scoring
- **Description analysis**: link count, timestamps, CTAs, first-line hook
- **Transcript analysis**: hook extraction (first 30s and 60s), retention markers, topic word extraction, chapter detection
- **Performance metrics**: engagement rate, like/comment ratios, views vs channel average, views per day
- **Channel context**: last 10 video titles with view counts, channel tier label

### Dashboard
- Breakout videos and recent uploads with tabbed view
- **Filtering**: channel size tier (nano to 1M+), sort by score/views/recency/engagement
- Keyword performance summary (which keywords produce the most breakouts)
- API quota tracking with visual bar
- Stats overview (total videos, breakouts, top score, saved count)

### Keyword Tracker
- 20 seed keywords for psychology/self-improvement niche
- Add/remove keywords from the UI
- Per-keyword refresh (saves quota — only searches that keyword)
- Google Trends integration with sparkline charts and direction indicators

### Saved Videos
- Bookmark any video to your personal collection
- Add/edit personal notes (hook structure, title formula, content angles)
- Copy all saved videos to clipboard
- Export as CSV

### Export
- CSV export of all breakout videos (from navbar)
- CSV export of saved collection (from saved page)

## API Quota Guide

YouTube Data API gives **10,000 units/day** free.

| Action | Cost |
|--------|------|
| search.list (per keyword) | 200 units (medium + long) |
| videos.list (batch of 50) | 1 unit |
| channels.list (batch of 50) | 1 unit |
| playlistItems.list | 1 unit |

A full refresh of 20 keywords uses ~4,000–6,000 units. Subsequent refreshes are cheaper because channel data is cached for 24 hours.

**Tips to save quota:**
- Use per-keyword refresh (hover keyword, click refresh icon) instead of refreshing all 20
- Channel data is cached 24h — second refresh the same day is much cheaper
- The quota bar in the navbar shows remaining daily units

## Outlier Score Formula

```
view_to_sub_ratio     = views / subscriber_count
view_to_average_ratio = views / channel_avg_views (excludes Shorts from avg)
outlier_score         = (view_to_sub_ratio * 0.4) + (view_to_average_ratio * 0.6)
```

Breakout threshold: any ratio >= 3 or combined score >= 3.

## Channel Size Tiers

| Tier | Subscribers |
|------|-------------|
| Nano | < 1K |
| Micro | 1K – 10K |
| Small | 10K – 100K |
| Medium | 100K – 1M |
| Large | 1M+ |

Filter by tier on the dashboard to find breakout patterns from channels your size.

## Stack

- **Backend**: Python, FastAPI, SQLite, google-api-python-client, youtube-transcript-api, pytrends
- **Frontend**: React 19, Vite 7, Tailwind CSS v4, @tanstack/react-query, lucide-react
