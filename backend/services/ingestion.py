import os
import time
import shutil
import subprocess
import yt_dlp
from pathlib import Path
from config import settings
from database import supabase


FFMPEG_BIN = r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"


def _remux_to_mp4(source_path: str, dest_path: str) -> bool:
    """
    Stream-copy source into an MP4 container with regenerated timestamps.
    Returns True on success, False on failure.
    """
    ext = Path(source_path).suffix.lower()
    if ext == ".mp4":
        return True  # nothing to do

    t0 = time.perf_counter()
    try:
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-fflags", "+genpts",
                "-i", source_path,
                "-c:v", "copy",
                "-c:a", "copy",
                dest_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"[INFO] Remuxed {ext} to MP4 in {elapsed_ms:.0f}ms")
        os.remove(source_path)
        return True
    except Exception as e:
        print(f"[WARN] Failed to remux {ext} to MP4: {e}")
        return False


def ingest(job: dict, job_id: str) -> str:
    """
    Downloads video (YouTube URL) or retrieves uploaded file from Supabase.
    Normalizes container to MP4 before returning.
    Returns local path to the video file.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(tmp_dir / "input.mp4")

    # Idempotency check — if input.mp4 already exists (including from a prior
    # remux of a non-MP4 source), skip all processing and return immediately.
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print("[INFO] Reusing existing downloaded video, skipping re-download")
        return output_path

    if job["source_type"] == "youtube_url":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([job["source_url"]])

        # Upload original to Supabase
        supabase.table("jobs").update({"storage_path": output_path}).eq("id", job_id).execute()

    elif job["source_type"] == "file_upload":
        local_path = job["storage_path"]
        src_ext = Path(local_path).suffix.lower()
        if src_ext != ".mp4":
            # Remux directly from the uploaded non-MP4 file into output_path
            _remux_to_mp4(local_path, output_path)
            return output_path
        if local_path != output_path:
            shutil.copy2(local_path, output_path)

    elif job["source_type"] == "local_path":
        local_path = job["source_url"] or job["storage_path"]
        local_path = local_path.strip().strip('"').strip("'")
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        src_ext = Path(local_path).suffix.lower()
        if src_ext != ".mp4":
            remux_path = str(Path(local_path).with_suffix(".mp4"))
            if _remux_to_mp4(local_path, remux_path):
                return remux_path
        return local_path

    return output_path