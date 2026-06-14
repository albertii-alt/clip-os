# ClipOS — Backend Setup Guide
> **Agent Instructions:** This file walks through the complete backend setup for ClipOS Phase 1. Execute steps in order. Do not skip steps. All commands assume Windows 11 with WSL2 (Ubuntu) or a native Ubuntu terminal. Python version must be 3.11+.

---

## Prerequisites Checklist

Before starting, confirm these are installed:

| Tool | Check Command | Min Version |
|---|---|---|
| Python | `python --version` | 3.11+ |
| pip | `pip --version` | latest |
| FFmpeg | `ffmpeg -version` | 6.0+ |
| Redis (Docker) | `docker --version` | any |
| Ollama | `ollama --version` | latest |
| llama3.1:8b pulled | `ollama list` | — |
| Git | `git --version` | any |

**Install FFmpeg (if missing):**
```bash
# Ubuntu / WSL2
sudo apt update && sudo apt install ffmpeg -y

# Verify
ffmpeg -version
```

**Start Ollama + pull model (if not done):**
```bash
ollama serve
ollama pull llama3.1:8b
```

---

## Step 1 — Project Folder Init

```bash
# From your projects root (e.g. D:/Projects or ~/projects)
mkdir clipos && cd clipos
mkdir backend frontend
cd backend
```

---

## Step 2 — Python Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (WSL2 / Linux)
source venv/bin/activate

# Activate (Windows CMD — if not using WSL)
venv\Scripts\activate

# Confirm
which python   # should point to venv
```

---

## Step 3 — Install Dependencies

```bash
pip install \
  fastapi==0.111.0 \
  uvicorn[standard]==0.30.1 \
  celery==5.4.0 \
  redis==5.0.7 \
  supabase==2.5.0 \
  faster-whisper==1.0.1 \
  yt-dlp==2024.5.27 \
  ffmpeg-python==0.2.0 \
  mediapipe==0.10.14 \
  opencv-python-headless==4.10.0.82 \
  httpx==0.27.0 \
  python-multipart==0.0.9 \
  python-dotenv==1.0.1 \
  pydantic==2.7.1 \
  pydantic-settings==2.2.1

# Save
pip freeze > requirements.txt
```

---

## Step 4 — Folder Structure

Run this to create all files at once:

```bash
# From inside /backend
mkdir -p routers services workers models

touch main.py
touch config.py
touch database.py
touch routers/__init__.py
touch routers/jobs.py
touch routers/clips.py
touch routers/campaigns.py
touch services/__init__.py
touch services/ingestion.py
touch services/transcription.py
touch services/analysis.py
touch services/video_processing.py
touch services/captioning.py
touch services/storage.py
touch workers/__init__.py
touch workers/celery_app.py
touch workers/pipeline.py
touch models/__init__.py
touch models/schemas.py
touch .env
touch .env.example
```

---

## Step 5 — Environment Variables

**`.env`** (fill in your real values):
```env
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Whisper
WHISPER_MODEL=medium

# Temp directory
TMP_DIR=/tmp/clipos
```

**`.env.example`** (safe to commit):
```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
WHISPER_MODEL=medium
TMP_DIR=/tmp/clipos
```

---

## Step 6 — Supabase Setup

### 6a. Create Project
1. Go to https://supabase.com → New Project
2. Name it `clipos`
3. Save your **Project URL** and **service_role key** (Settings → API)
4. Put them in `.env`

### 6b. Create Storage Bucket
1. Supabase Dashboard → Storage → New Bucket
2. Name: `clipos-assets`
3. Set to **Public** (so clip URLs work without auth in Phase 1)

### 6c. Run Database Migrations

Go to Supabase Dashboard → SQL Editor → paste and run each block:

```sql
-- campaigns table
CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  creator_handle TEXT,
  platform TEXT NOT NULL,
  payout_per_1k NUMERIC(10,2),
  min_clip_length INT DEFAULT 30,
  max_clip_length INT DEFAULT 60,
  required_hashtags TEXT[] DEFAULT '{}',
  required_tags TEXT[] DEFAULT '{}',
  forbidden_topics TEXT[] DEFAULT '{}',
  style_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

```sql
-- jobs table
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  source_type TEXT NOT NULL,
  source_url TEXT,
  original_filename TEXT,
  storage_path TEXT,
  status TEXT DEFAULT 'queued',
  error_message TEXT,
  transcript_path TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

```sql
-- clips table
CREATE TABLE clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  clip_index INT,
  start_time NUMERIC(10,3),
  end_time NUMERIC(10,3),
  hook TEXT,
  category TEXT,
  viral_score INT,
  score_reason TEXT,
  storage_path TEXT,
  public_url TEXT,
  views INT DEFAULT 0,
  earnings NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

```sql
-- Auto-update updated_at on jobs
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Step 7 — Redis via Docker

```bash
# Start Redis container
docker run -d \
  --name clipos-redis \
  -p 6379:6379 \
  redis:alpine

# Verify
docker ps
# You should see clipos-redis running

# Test connection
docker exec -it clipos-redis redis-cli ping
# Expected: PONG
```

---

## Step 8 — Boilerplate Code

Paste each block into the corresponding file.

### `config.py`
```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    whisper_model: str = "medium"
    tmp_dir: str = "/tmp/clipos"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure tmp dir exists
Path(settings.tmp_dir).mkdir(parents=True, exist_ok=True)
```

---

### `database.py`
```python
from supabase import create_client, Client
from config import settings

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key
)
```

---

### `models/schemas.py`
```python
from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime


# ── Campaigns ──────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str
    creator_handle: Optional[str] = None
    platform: str
    payout_per_1k: Optional[float] = None
    min_clip_length: int = 30
    max_clip_length: int = 60
    required_hashtags: List[str] = []
    required_tags: List[str] = []
    forbidden_topics: List[str] = []
    style_notes: Optional[str] = None


class CampaignUpdate(CampaignCreate):
    pass


class Campaign(CampaignCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Jobs ───────────────────────────────────────────────────
class JobCreate(BaseModel):
    source_type: str          # 'youtube_url' | 'file_upload'
    source_url: Optional[str] = None
    campaign_id: Optional[str] = None


class Job(BaseModel):
    id: str
    campaign_id: Optional[str]
    source_type: str
    source_url: Optional[str]
    original_filename: Optional[str]
    storage_path: Optional[str]
    status: str
    error_message: Optional[str]
    transcript_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Clips ──────────────────────────────────────────────────
class ClipUpdate(BaseModel):
    views: Optional[int] = None
    earnings: Optional[float] = None


class Clip(BaseModel):
    id: str
    job_id: str
    clip_index: int
    start_time: float
    end_time: float
    hook: Optional[str]
    category: Optional[str]
    viral_score: Optional[int]
    score_reason: Optional[str]
    storage_path: Optional[str]
    public_url: Optional[str]
    views: int
    earnings: float
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### `main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import jobs, clips, campaigns

app = FastAPI(
    title="ClipOS API",
    description="AI-powered Whop clipping automation backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(clips.router, prefix="/clips", tags=["Clips"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ClipOS API"}
```

---

### `routers/campaigns.py`
```python
from fastapi import APIRouter, HTTPException
from database import supabase
from models.schemas import CampaignCreate, CampaignUpdate

router = APIRouter()


@router.get("/")
def list_campaigns():
    result = supabase.table("campaigns").select("*").order("created_at", desc=True).execute()
    return result.data


@router.post("/", status_code=201)
def create_campaign(payload: CampaignCreate):
    result = supabase.table("campaigns").insert(payload.model_dump()).execute()
    return result.data[0]


@router.put("/{campaign_id}")
def update_campaign(campaign_id: str, payload: CampaignUpdate):
    result = supabase.table("campaigns").update(payload.model_dump()).eq("id", campaign_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str):
    supabase.table("campaigns").delete().eq("id", campaign_id).execute()
```

---

### `routers/jobs.py`
```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from database import supabase
from workers.pipeline import run_pipeline
import uuid

router = APIRouter()


@router.get("/")
def list_jobs():
    result = supabase.table("jobs").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{job_id}")
def get_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data


@router.post("/", status_code=201)
async def create_job(
    source_type: str = Form(...),
    source_url: Optional[str] = Form(None),
    campaign_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    job_id = str(uuid.uuid4())

    # Insert job row
    job_data = {
        "id": job_id,
        "source_type": source_type,
        "source_url": source_url,
        "campaign_id": campaign_id,
        "status": "queued"
    }

    if file:
        # Save uploaded file to Supabase Storage
        file_bytes = await file.read()
        storage_path = f"videos/originals/{job_id}.mp4"
        supabase.storage.from_("clipos-assets").upload(storage_path, file_bytes)
        job_data["storage_path"] = storage_path
        job_data["original_filename"] = file.filename

    supabase.table("jobs").insert(job_data).execute()

    # Queue the pipeline task
    run_pipeline.delay(job_id)

    return {"job_id": job_id, "status": "queued"}
```

---

### `routers/clips.py`
```python
from fastapi import APIRouter, HTTPException
from database import supabase
from models.schemas import ClipUpdate

router = APIRouter()


@router.get("/{job_id}")
def get_clips_for_job(job_id: str):
    result = (
        supabase.table("clips")
        .select("*")
        .eq("job_id", job_id)
        .order("viral_score", desc=True)
        .execute()
    )
    return result.data


@router.patch("/{clip_id}")
def update_clip(clip_id: str, payload: ClipUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = supabase.table("clips").update(updates).eq("id", clip_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Clip not found")
    return result.data[0]
```

---

### `workers/celery_app.py`
```python
from celery import Celery
from config import settings

celery_app = Celery(
    "clipos",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.pipeline"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
)
```

---

### `workers/pipeline.py`
```python
from workers.celery_app import celery_app
from database import supabase
from services import ingestion, transcription, analysis, video_processing
import traceback


def update_job_status(job_id: str, status: str, error: str = None):
    update = {"status": status}
    if error:
        update["error_message"] = error
    supabase.table("jobs").update(update).eq("id", job_id).execute()


@celery_app.task(bind=True, max_retries=1)
def run_pipeline(self, job_id: str):
    try:
        # Fetch job
        result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        job = result.data

        # Fetch campaign if attached
        campaign = None
        if job.get("campaign_id"):
            camp_result = supabase.table("campaigns").select("*").eq("id", job["campaign_id"]).single().execute()
            campaign = camp_result.data

        # Step 1: Ingest
        update_job_status(job_id, "downloading")
        video_path = ingestion.ingest(job, job_id)

        # Step 2: Transcribe
        update_job_status(job_id, "transcribing")
        transcript = transcription.transcribe(video_path, job_id)

        # Step 3: Analyze
        update_job_status(job_id, "analyzing")
        moments = analysis.analyze(transcript, campaign)

        # Step 4: Render clips
        update_job_status(job_id, "rendering")
        video_processing.render_clips(video_path, moments, job_id)

        # Done
        update_job_status(job_id, "done")

    except Exception as e:
        update_job_status(job_id, "failed", error=traceback.format_exc())
        raise self.retry(exc=e, countdown=5)
```

---

### `services/ingestion.py`
```python
import yt_dlp
import os
from pathlib import Path
from config import settings
from database import supabase


def ingest(job: dict, job_id: str) -> str:
    """
    Downloads video (YouTube URL) or retrieves uploaded file from Supabase.
    Returns local path to the video file.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(tmp_dir / "input.mp4")

    if job["source_type"] == "youtube_url":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([job["source_url"]])

        # Upload original to Supabase
        storage_path = f"videos/originals/{job_id}.mp4"
        with open(output_path, "rb") as f:
            supabase.storage.from_("clipos-assets").upload(storage_path, f)
        supabase.table("jobs").update({"storage_path": storage_path}).eq("id", job_id).execute()

    elif job["source_type"] == "file_upload":
        # Download from Supabase Storage to tmp
        storage_path = job["storage_path"]
        file_bytes = supabase.storage.from_("clipos-assets").download(storage_path)
        with open(output_path, "wb") as f:
            f.write(file_bytes)

    return output_path
```

---

### `services/transcription.py`
```python
import json
import ffmpeg
from pathlib import Path
from faster_whisper import WhisperModel
from config import settings
from database import supabase


def transcribe(video_path: str, job_id: str) -> list[dict]:
    """
    Extracts audio from video, runs Faster-Whisper, returns word-level segments.
    Also uploads transcript JSON to Supabase Storage.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    audio_path = str(tmp_dir / "audio.wav")

    # Extract audio
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar=16000)
        .overwrite_output()
        .run(quiet=True)
    )

    # Transcribe
    model = WhisperModel(settings.whisper_model, device="cuda", compute_type="float16")
    segments, _ = model.transcribe(audio_path, word_timestamps=True)

    # Build flat word list with timestamps
    words = []
    full_segments = []
    for segment in segments:
        seg_data = {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
            "words": []
        }
        for word in (segment.words or []):
            w = {
                "word": word.word.strip(),
                "start": round(word.start, 3),
                "end": round(word.end, 3)
            }
            seg_data["words"].append(w)
            words.append(w)
        full_segments.append(seg_data)

    transcript_data = {"segments": full_segments, "words": words}

    # Save + upload to Supabase
    transcript_path_local = str(tmp_dir / "transcript.json")
    with open(transcript_path_local, "w") as f:
        json.dump(transcript_data, f)

    storage_path = f"transcripts/{job_id}.json"
    with open(transcript_path_local, "rb") as f:
        supabase.storage.from_("clipos-assets").upload(storage_path, f)

    supabase.table("jobs").update({"transcript_path": storage_path}).eq("id", job_id).execute()

    return full_segments
```

---

### `services/analysis.py`
```python
import httpx
import json
import re
from config import settings


ANALYSIS_PROMPT = """
You are an expert short-form content strategist specializing in viral clip selection.

Analyze the following transcript and find the TOP 5 most clip-worthy moments.

## Campaign Rules
{campaign_rules}

## Transcript
{transcript_text}

## Selection Criteria
- Hook strength: Does the first sentence stop a scroller?
- Emotional impact: Does it create feeling (loss, inspiration, shock, humor)?
- Curiosity gap: Does it make someone want to know more?
- Novelty: Is this surprising or counter-intuitive?
- Completeness: Can it stand alone without context?

## Output Format
Return ONLY a valid JSON array. No explanation. No markdown. No extra text.

[
  {{
    "start": "HH:MM:SS",
    "end": "HH:MM:SS",
    "hook": "Rewritten opening line optimized for retention",
    "category": "emotional_story | controversy | educational | funny | curiosity_gap",
    "score": 0,
    "reason": "One sentence explaining why this moment works"
  }}
]

Rules:
- Each clip must be between {min_length}s and {max_length}s
- Avoid topics: {forbidden_topics}
- Return exactly 5 moments, sorted by score descending
"""


def format_campaign_rules(campaign: dict | None) -> str:
    if not campaign:
        return "No specific campaign rules. Select general high-retention moments."
    return (
        f"Platform: {campaign.get('platform', 'any')}\n"
        f"Required hashtags: {', '.join(campaign.get('required_hashtags', []))}\n"
        f"Required tags: {', '.join(campaign.get('required_tags', []))}\n"
        f"Clip length: {campaign.get('min_clip_length', 30)}s to {campaign.get('max_clip_length', 60)}s\n"
        f"Forbidden topics: {', '.join(campaign.get('forbidden_topics', []))}\n"
        f"Style notes: {campaign.get('style_notes', 'none')}"
    )


def timestamp_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s


def analyze(segments: list[dict], campaign: dict | None) -> list[dict]:
    """
    Sends transcript to Ollama LLM and returns list of viral moments.
    """
    transcript_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in segments
    )

    min_length = campaign.get("min_clip_length", 30) if campaign else 30
    max_length = campaign.get("max_clip_length", 60) if campaign else 60
    forbidden = ", ".join(campaign.get("forbidden_topics", [])) if campaign else "none"

    prompt = ANALYSIS_PROMPT.format(
        campaign_rules=format_campaign_rules(campaign),
        transcript_text=transcript_text,
        min_length=min_length,
        max_length=max_length,
        forbidden_topics=forbidden
    )

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False
        },
        timeout=120.0
    )
    response.raise_for_status()
    raw = response.json().get("response", "")

    # Defensive JSON extraction
    try:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in LLM response")
        moments = json.loads(match.group())
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {e}\nRaw: {raw}")

    # Convert timestamps to seconds
    for m in moments:
        m["start_seconds"] = timestamp_to_seconds(m["start"])
        m["end_seconds"] = timestamp_to_seconds(m["end"])

    return moments
```

---

### `services/video_processing.py`
```python
import ffmpeg
import uuid
from pathlib import Path
from config import settings
from database import supabase
from services.captioning import generate_ass_subtitles


def get_face_crop_x(video_path: str, width: int, height: int) -> int:
    """
    Basic center crop for now. MediaPipe face detection can replace this later.
    Returns x offset for 9:16 crop from 16:9 source.
    """
    target_width = int(height * 9 / 16)
    return max(0, (width - target_width) // 2)


def render_clips(video_path: str, moments: list[dict], job_id: str):
    """
    For each moment: cut → reframe to 9:16 → burn captions → upload to Supabase.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    clips_dir = tmp_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Get video dimensions
    probe = ffmpeg.probe(video_path)
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    orig_width = int(video_stream["width"])
    orig_height = int(video_stream["height"])

    for idx, moment in enumerate(moments, start=1):
        start = moment["start_seconds"]
        end = moment["end_seconds"]
        duration = end - start
        clip_id = str(uuid.uuid4())

        raw_clip_path = str(clips_dir / f"raw_{idx}.mp4")
        final_clip_path = str(clips_dir / f"clip_{idx}.mp4")
        ass_path = str(clips_dir / f"clip_{idx}.ass")

        # Step 1: Cut raw clip
        (
            ffmpeg
            .input(video_path, ss=start, t=duration)
            .output(raw_clip_path, c="copy")
            .overwrite_output()
            .run(quiet=True)
        )

        # Step 2: Generate ASS captions
        # Load full transcript from tmp
        import json
        with open(str(tmp_dir / "transcript.json")) as f:
            transcript = json.load(f)
        generate_ass_subtitles(transcript["words"], start, end, ass_path)

        # Step 3: Reframe 16:9 → 9:16 + burn captions
        target_h = orig_height
        target_w = int(orig_height * 9 / 16)
        crop_x = get_face_crop_x(video_path, orig_width, orig_height)

        (
            ffmpeg
            .input(raw_clip_path)
            .filter("crop", target_w, target_h, crop_x, 0)
            .filter("scale", 1080, 1920)
            .output(
                final_clip_path,
                vf=f"subtitles={ass_path}",
                vcodec="libx264",
                acodec="aac",
                crf=23,
                preset="fast"
            )
            .overwrite_output()
            .run(quiet=True)
        )

        # Step 4: Upload to Supabase
        storage_path = f"clips/{job_id}/clip_{idx}.mp4"
        with open(final_clip_path, "rb") as f:
            supabase.storage.from_("clipos-assets").upload(storage_path, f)

        public_url = supabase.storage.from_("clipos-assets").get_public_url(storage_path)

        # Step 5: Insert clip row
        supabase.table("clips").insert({
            "id": clip_id,
            "job_id": job_id,
            "clip_index": idx,
            "start_time": start,
            "end_time": end,
            "hook": moment.get("hook"),
            "category": moment.get("category"),
            "viral_score": moment.get("score"),
            "score_reason": moment.get("reason"),
            "storage_path": storage_path,
            "public_url": public_url
        }).execute()

    # Cleanup tmp files
    import shutil
    shutil.rmtree(str(tmp_dir), ignore_errors=True)
```

---

### `services/captioning.py`
```python
def seconds_to_ass_time(s: float) -> str:
    """Convert float seconds to ASS timestamp format H:MM:SS.cc"""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{int(sec):02d}.{cs:02d}"


def generate_ass_subtitles(
    words: list[dict],
    clip_start: float,
    clip_end: float,
    output_path: str
):
    """
    Generates TikTok-style ASS subtitle file for a clip.
    Words are filtered to the clip's time range and timestamps are offset.
    """
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,5,60,60,960,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = []
    clip_words = [w for w in words if w["start"] >= clip_start and w["end"] <= clip_end]

    # Group into lines of 4 words max
    chunk_size = 4
    for i in range(0, len(clip_words), chunk_size):
        chunk = clip_words[i:i + chunk_size]
        if not chunk:
            continue

        start_ts = seconds_to_ass_time(chunk[0]["start"] - clip_start)
        end_ts = seconds_to_ass_time(chunk[-1]["end"] - clip_start)
        text = " ".join(w["word"].upper() for w in chunk)

        lines.append(
            f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(lines))
```

---

## Step 9 — Run Everything

Open **4 terminal windows:**

```bash
# Terminal 1 — FastAPI server
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Celery worker
cd backend
source venv/bin/activate
celery -A workers.celery_app worker --loglevel=info

# Terminal 3 — Redis (if not running as daemon)
docker start clipos-redis

# Terminal 4 — Ollama
ollama serve
```

---

## Step 10 — Test the Pipeline

```bash
# Health check
curl http://localhost:8000/health

# Create a campaign
curl -X POST http://localhost:8000/campaigns/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Campaign",
    "platform": "tiktok",
    "min_clip_length": 30,
    "max_clip_length": 60,
    "required_hashtags": ["#testcampaign"],
    "required_tags": ["@testcreator"],
    "forbidden_topics": [],
    "style_notes": "Focus on emotional moments"
  }'

# Submit a YouTube URL job
curl -X POST http://localhost:8000/jobs/ \
  -F "source_type=youtube_url" \
  -F "source_url=https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  -F "campaign_id=YOUR_CAMPAIGN_UUID"

# Poll job status
curl http://localhost:8000/jobs/YOUR_JOB_ID

# Get clips when done
curl http://localhost:8000/clips/YOUR_JOB_ID
```

---

## Common Issues & Fixes

| Issue | Fix |
|---|---|
| `faster-whisper` CUDA error | Set `device="cpu"` in `transcription.py` for testing |
| Ollama timeout | Increase `timeout=120.0` in `analysis.py` or use `qwen2.5-coder:7b` |
| FFmpeg not found | Ensure `ffmpeg` is in PATH: `which ffmpeg` |
| Redis connection refused | Run `docker start clipos-redis` |
| Supabase upload 403 | Check bucket is set to Public in Supabase Dashboard |
| JSON parse error from LLM | Check Ollama logs; try switching to `llama3.1:8b` |
| Large video OOM | Lower Whisper model to `base` or `small` |

---

## Next File

Once Phase 1 backend is working, the next setup file is:  
**`CLIPOS_FRONTEND_SETUP.md`** — Next.js dashboard with upload form, job status polling, and clip preview grid.
