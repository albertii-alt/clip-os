import yt_dlp
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