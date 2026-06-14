# ClipOS — AI Clipping Automation System
> **Agent Instructions:** This is the single source of truth for the ClipOS project. Read this file fully before generating any code, suggesting any architecture, or making any implementation decisions. Do not deviate from the stack, folder structure, or phase boundaries defined here without explicit user instruction.

---

## 1. Project Overview

**Name:** ClipOS  
**Purpose:** A personal AI-powered clipping automation system built to earn real income from Whop clipping campaigns. The developer (Jay-ar) is the primary user. SaaS potential is secondary.

**What it does:**
- Accepts a YouTube URL or MP4 upload
- Transcribes the video using Faster-Whisper
- Uses a local LLM (via Ollama) to detect viral-worthy moments
- Extracts, reframes (16:9 → 9:16), and renders short clips using FFmpeg
- Burns TikTok-style captions into clips
- Respects per-campaign rules (hashtags, length, platform, style)
- Stores all assets and metadata in Supabase

**Income model:** Clipping campaigns on Whop pay per views (e.g. $5 per 1,000 views). More quality clips posted = more potential earnings.

**Core insight:** The system does NOT guarantee virality. It eliminates bad clips faster, increases daily output volume, and ensures campaign compliance (correct hashtags, length, format) so views are never disqualified.

---

## 2. Developer Context

- **Developer:** Jay-ar (Alberto Jr. Auxtero Daro)
- **Coding agents:** Amazon Q (VS Code), Kiro IDE, Gemini Code Assist
- **Hardware:** 16GB RAM, RTX 3050 6GB VRAM, 12th Gen i5-12450HX
- **Local LLM setup:** Ollama running `llama3.1:8b` (chat/agent) and `qwen2.5-coder:7b` (autocomplete)
- **Experience:** Full-stack apps (React, Node.js, Java), POS systems, dental clinic management system, portfolio site

> **Agent note:** Do not suggest cloud LLM APIs (OpenAI, Anthropic, Gemini) for the AI pipeline in Phase 1 or 2. Use local Ollama endpoints. The developer's GPU can handle 7B–8B models.

---

## 3. Tech Stack (Locked)

### Frontend
| Layer | Choice | Notes |
|---|---|---|
| Framework | Next.js 14+ (App Router) | TypeScript only |
| Styling | Tailwind CSS v4 | No CSS modules |
| UI Components | shadcn/ui | Install via CLI as needed |
| Animations | Framer Motion | Minimal, purposeful |
| State | Zustand | For global job/clip state |
| HTTP Client | Axios or fetch | Prefer native fetch with SWR for polling |

### Backend
| Layer | Choice | Notes |
|---|---|---|
| Framework | FastAPI (Python 3.11+) | Async where possible |
| Task Queue | Celery + Redis | All video processing runs as background jobs |
| Video Download | yt-dlp | Python library, not CLI subprocess |
| Transcription | faster-whisper | Use `large-v2` model if VRAM allows, else `medium` |
| LLM | Ollama HTTP API | `http://localhost:11434/api/generate` |
| LLM Model | `llama3.1:8b` or `qwen2.5-coder:7b` | Use llama3.1 for reasoning tasks |
| Video Processing | ffmpeg-python | Wrapper around FFmpeg binary |
| Speaker Detection | mediapipe | Face mesh for crop centering |
| File Storage | Supabase Storage | Bucket: `clipos-assets` |
| Database | Supabase PostgreSQL | Via supabase-py |

### Infrastructure
| Layer | Choice | Notes |
|---|---|---|
| Database + Storage | Supabase (free tier) | Single platform for DB + file storage |
| Cache / Queue Broker | Redis (local Docker) | `redis:alpine` container |
| Frontend Deploy | Vercel | Auto-deploy from main branch |
| Backend Deploy | Local machine (Phase 1–2), Render (Phase 3+) | Start local, deploy later |

> **Agent note:** Do NOT add new dependencies without checking this list first. If a package is not listed here, ask before installing.

---

## 4. Folder Structure

```
clipos/
├── frontend/                        # Next.js app
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx             # Main dashboard — job list
│   │   │   ├── upload/page.tsx      # Upload + YouTube URL input
│   │   │   ├── campaigns/page.tsx   # Campaign profile manager
│   │   │   └── clips/[jobId]/page.tsx  # Clip preview + download
│   │   ├── api/
│   │   │   └── proxy/route.ts       # Optional: proxy to FastAPI
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   ├── ClipCard.tsx
│   │   ├── JobStatusBadge.tsx
│   │   ├── UploadForm.tsx
│   │   └── CampaignForm.tsx
│   ├── lib/
│   │   ├── api.ts                   # API client functions
│   │   └── supabase.ts              # Supabase browser client
│   └── stores/
│       └── jobStore.ts              # Zustand store
│
├── backend/                         # FastAPI app
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Env vars, settings
│   ├── database.py                  # Supabase client init
│   ├── routers/
│   │   ├── jobs.py                  # POST /jobs, GET /jobs/{id}
│   │   ├── clips.py                 # GET /clips/{job_id}
│   │   └── campaigns.py             # CRUD /campaigns
│   ├── services/
│   │   ├── ingestion.py             # yt-dlp download + upload to Supabase
│   │   ├── transcription.py         # faster-whisper wrapper
│   │   ├── analysis.py              # Ollama LLM viral moment detection
│   │   ├── video_processing.py      # ffmpeg-python clip extraction + reframe
│   │   ├── captioning.py            # ASS subtitle generation + FFmpeg burn-in
│   │   └── storage.py               # Supabase Storage upload/download helpers
│   ├── workers/
│   │   ├── celery_app.py            # Celery instance + config
│   │   └── pipeline.py              # Main Celery task: full pipeline chain
│   ├── models/
│   │   └── schemas.py               # Pydantic schemas
│   └── requirements.txt
│
├── docker-compose.yml               # Redis only (for local dev)
├── .env.example
└── CLIPOS_PROJECT.md                # THIS FILE — project spec
```

---

## 5. Database Schema

### Table: `campaigns`
```sql
CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  creator_handle TEXT,
  platform TEXT NOT NULL,          -- 'tiktok' | 'youtube_shorts' | 'instagram_reels'
  payout_per_1k NUMERIC(10,2),
  min_clip_length INT DEFAULT 30,  -- seconds
  max_clip_length INT DEFAULT 60,  -- seconds
  required_hashtags TEXT[],
  required_tags TEXT[],
  forbidden_topics TEXT[],
  style_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Table: `jobs`
```sql
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id),
  source_type TEXT NOT NULL,       -- 'youtube_url' | 'file_upload'
  source_url TEXT,
  original_filename TEXT,
  storage_path TEXT,               -- Supabase Storage path to original video
  status TEXT DEFAULT 'queued',    -- 'queued' | 'downloading' | 'transcribing' | 'analyzing' | 'rendering' | 'done' | 'failed'
  error_message TEXT,
  transcript_path TEXT,            -- Supabase Storage path to transcript JSON
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Table: `clips`
```sql
CREATE TABLE clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id),
  clip_index INT,                  -- order within job (1, 2, 3...)
  start_time NUMERIC(10,3),        -- seconds
  end_time NUMERIC(10,3),          -- seconds
  hook TEXT,
  category TEXT,                   -- 'emotional_story' | 'controversy' | 'educational' | 'funny' | 'curiosity_gap'
  viral_score INT,                 -- 0-100
  score_reason TEXT,
  storage_path TEXT,               -- Supabase Storage path to rendered clip
  public_url TEXT,                 -- Signed/public URL for preview
  views INT DEFAULT 0,             -- Manual input after posting
  earnings NUMERIC(10,2),          -- Manual input
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Core Pipeline (Step by Step)

Every job runs through this exact pipeline as a Celery task chain:

```
POST /jobs  (YouTube URL or file upload)
     |
     v
[Step 1] INGEST
  - Download via yt-dlp (if YouTube URL)
  - OR receive uploaded file
  - Upload original to Supabase Storage: videos/originals/{job_id}.mp4
  - Update job status: 'downloading'

     |
     v
[Step 2] TRANSCRIBE
  - Download video from Supabase to /tmp/{job_id}/input.mp4
  - Extract audio: ffmpeg → audio.wav
  - Run faster-whisper → word-level timestamped transcript
  - Save transcript JSON to Supabase: transcripts/{job_id}.json
  - Update job status: 'transcribing'

     |
     v
[Step 3] ANALYZE
  - Load transcript JSON
  - Load campaign rules (if campaign_id attached to job)
  - Build LLM prompt (see Section 7)
  - Call Ollama API → parse JSON response → top 5 moments
  - Update job status: 'analyzing'

     |
     v
[Step 4] RENDER
  - For each moment:
      a. FFmpeg cut: start_time → end_time
      b. MediaPipe face detection → calculate crop center
      c. FFmpeg reframe: 16:9 → 9:16 (1080x1920)
      d. Generate ASS subtitle file from Whisper word timestamps
      e. FFmpeg burn captions into clip
      f. Upload to Supabase: clips/{job_id}/clip_{n}.mp4
      g. Insert row into `clips` table
  - Update job status: 'done'
  - Clean up /tmp/{job_id}/

     |
     v
[Step 5] NOTIFY
  - Update job.updated_at
  - Frontend polls GET /jobs/{id} every 3s to show status
```

---

## 7. LLM Prompt Template

This is the exact prompt structure to use when calling Ollama for viral moment detection.

```python
ANALYSIS_PROMPT = """
You are an expert short-form content strategist specializing in viral clip selection.

Analyze the following transcript and find the TOP 5 most clip-worthy moments.

## Campaign Rules
{campaign_rules}

## Transcript
{transcript_text}

## Selection Criteria (score each on these factors)
- Hook strength: Does the first sentence stop a scroller?
- Emotional impact: Does it create feeling (loss, inspiration, shock, humor)?
- Curiosity gap: Does it make someone want to know more?
- Novelty: Is this surprising or counter-intuitive?
- Completeness: Can it stand alone without context?

## Output Format
Return ONLY a valid JSON array. No explanation. No markdown. No extra text.

[
  {
    "start": "HH:MM:SS",
    "end": "HH:MM:SS",
    "hook": "Rewritten opening line optimized for retention",
    "category": "emotional_story | controversy | educational | funny | curiosity_gap",
    "score": 0-100,
    "reason": "One sentence explaining why this moment works"
  }
]

Rules:
- Each clip must be between {min_length}s and {max_length}s
- Avoid: {forbidden_topics}
- Return exactly 5 moments, sorted by score descending
"""
```

> **Agent note:** Always strip the Ollama response to extract the JSON array only. The model may prepend text. Use a regex or `response.split('[')[1]` approach to isolate JSON.

---

## 8. Campaign Rules Context (Injected into Prompt)

When a job has a `campaign_id`, load the campaign and format rules like:

```python
def format_campaign_rules(campaign: dict) -> str:
    if not campaign:
        return "No specific campaign rules. Select general high-retention moments."
    
    return f"""
- Platform: {campaign['platform']}
- Required hashtags to include in export metadata: {', '.join(campaign['required_hashtags'])}
- Required account tags: {', '.join(campaign['required_tags'])}
- Clip length: {campaign['min_clip_length']}s to {campaign['max_clip_length']}s
- Forbidden topics: {', '.join(campaign['forbidden_topics'])}
- Style notes: {campaign['style_notes']}
"""
```

---

## 9. API Endpoints

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs` | Create job (YouTube URL or file upload) |
| GET | `/jobs` | List all jobs |
| GET | `/jobs/{job_id}` | Get job status + details |

### Clips
| Method | Endpoint | Description |
|---|---|---|
| GET | `/clips/{job_id}` | Get all clips for a job |
| PATCH | `/clips/{clip_id}` | Update views/earnings (manual input) |

### Campaigns
| Method | Endpoint | Description |
|---|---|---|
| GET | `/campaigns` | List all campaigns |
| POST | `/campaigns` | Create campaign |
| PUT | `/campaigns/{id}` | Update campaign |
| DELETE | `/campaigns/{id}` | Delete campaign |

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Returns `{ status: "ok" }` |

---

## 10. Caption Style

TikTok-style captions burned into clips via FFmpeg ASS subtitles.

**Spec:**
- Font: Arial Black or Impact
- Size: 18–22pt (relative to 1080x1920)
- Color: White with black stroke/outline
- Position: Center screen (not bottom — avoids TikTok UI overlap)
- Style: Word-by-word highlight (current word turns yellow/green)
- Max words per line: 4–5
- All caps

**ASS subtitle generation** is handled in `captioning.py` using Whisper word-level timestamps.

---

## 11. Environment Variables

```env
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Whisper
WHISPER_MODEL=medium        # or large-v2 if VRAM allows

# Temp directory
TMP_DIR=/tmp/clipos

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

---

## 12. Build Phases

### Phase 1 — Core Pipeline (Current Goal)
- [ ] FastAPI project setup + all routers
- [ ] Supabase tables created
- [ ] Redis + Celery running via Docker
- [ ] Ingestion service (yt-dlp + Supabase upload)
- [ ] Transcription service (faster-whisper)
- [ ] Analysis service (Ollama LLM)
- [ ] Video processing service (FFmpeg cut + reframe)
- [ ] Captioning service (ASS + burn-in)
- [ ] Full pipeline wired as Celery task chain
- [ ] Next.js dashboard: upload form + job status + clip preview + download

### Phase 2 — Campaign Profiles
- [ ] Campaign CRUD (backend + frontend)
- [ ] Campaign rules injected into LLM prompt
- [ ] FFmpeg respects min/max clip length per campaign
- [ ] Export metadata (hashtags, tags) included in clip download package

### Phase 3 — Feedback Loop
- [ ] Manual views/earnings input per clip
- [ ] Analytics dashboard: earnings per campaign, best-performing categories
- [ ] Clip history with performance data
- [ ] LLM prompt tuning based on high-performing clip patterns

### Phase 4 — Polish / Optional SaaS
- [ ] Auth (Supabase Auth)
- [ ] Multi-user support
- [ ] Backend deployment (Render or Fly.io)
- [ ] Clip scheduling / direct publish integration (TikTok API, if available)

---

## 13. Development Rules (For AI Agents)

1. **Always read this file first** before writing code for any feature.
2. **Never install packages not in the stack** without checking Section 3.
3. **All video processing is async** — no blocking calls in FastAPI route handlers. Use Celery tasks.
4. **Temp files live in `/tmp/clipos/{job_id}/`** and are cleaned up after each job.
5. **Supabase Storage paths follow this convention:**
   - Originals: `videos/originals/{job_id}.mp4`
   - Transcripts: `transcripts/{job_id}.json`
   - Clips: `clips/{job_id}/clip_{n}.mp4`
6. **LLM responses must be parsed defensively.** Always wrap Ollama output parsing in try/except. Log malformed responses and retry once before failing the job.
7. **Job status must be updated at every pipeline step.** The frontend polls status — stale statuses break UX.
8. **Never hardcode credentials.** All secrets via `.env` / environment variables.
9. **TypeScript strict mode is ON** in the frontend. No `any` types without justification.
10. **Python type hints are required** on all function signatures in the backend.
