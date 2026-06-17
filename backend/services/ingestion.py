import os
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

    # Idempotency check — reuse existing download
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print("[INFO] Reusing existing downloaded video, skipping re-download")
        return output_path

    if job["source_type"] == "youtube_url":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin",  # ← add this line with your actual path
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([job["source_url"]])

        # Upload original to Supabase
        supabase.table("jobs").update({"storage_path": output_path}).eq("id", job_id).execute()

    elif job["source_type"] == "file_upload":
        # File already saved locally during upload
        local_path = job["storage_path"]
        if local_path != output_path:
            import shutil
            shutil.copy2(local_path, output_path)

    elif job["source_type"] == "local_path":
        local_path = job["source_url"] or job["storage_path"]
        # Strip surrounding quotes if present
        local_path = local_path.strip().strip('"').strip("'")
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        return local_path

    return output_path