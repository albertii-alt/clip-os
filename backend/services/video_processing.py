import json
import uuid
import ffmpeg
from pathlib import Path
from config import settings
from database import supabase
from services.captioning import generate_ass_subtitles


def get_face_crop_x(video_path: str, width: int, height: int) -> int:
    """
    Basic center crop. MediaPipe face detection can replace this later.
    Returns x offset for 9:16 crop from 16:9 source.
    """
    target_width = int(height * 9 / 16)
    return max(0, (width - target_width) // 2)


def render_clips(video_path: str, moments: list[dict], job_id: str, campaign: dict | None = None):
    """
    For each moment: cut → reframe to 9:16 → burn captions → upload to Supabase.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    clips_dir = tmp_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Get video dimensions
    probe = ffmpeg.probe(video_path, cmd=r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe")
    video_stream = next(
        (s for s in probe["streams"] if s["codec_type"] == "video"),
        None
    )
    if video_stream is None:
        raise ValueError("No video stream found in file")
    orig_width = int(video_stream["width"])
    orig_height = int(video_stream["height"])

    # Load transcript for captions
    with open(str(tmp_dir / "transcript.json")) as f:
        transcript = json.load(f)

    # Enforce campaign clip length constraints
    min_length = 15  # default
    max_length = 120  # default
    if campaign:
        min_length = campaign.get("min_clip_length", 15)
        max_length = campaign.get("max_clip_length", 120)

    original_moments = moments
    filtered_moments = []
    for m in moments:
        dur = m["end_seconds"] - m["start_seconds"]
        if min_length <= dur <= max_length:
            filtered_moments.append(m)
        else:
            print(f"[INFO] Skipping moment {m.get('start')} - {m.get('end')}: duration {dur:.1f}s outside {min_length}s-{max_length}s")

    moments = filtered_moments
    if not moments:
        print("[WARN] All moments filtered out by campaign length constraints — using original unfiltered moments")
        moments = original_moments

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
            .run(quiet=False, cmd=r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
        )

        # Step 2: Generate ASS captions
        generate_ass_subtitles(
            transcript["words"],
            start,
            end,
            ass_path,
            segments=transcript.get("segments", [])
        )

        # Step 3: Reframe 16:9 → 9:16 + burn captions
        target_h = orig_height
        target_w = int(orig_height * 9 / 16)
        crop_x = get_face_crop_x(video_path, orig_width, orig_height)

        # Escape path for FFmpeg subtitle filter on Windows
        ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        (
            ffmpeg
            .input(raw_clip_path)
            .output(
                final_clip_path,
                vf=f"crop={target_w}:{target_h}:{crop_x}:0,scale=1080:1920,subtitles='{ass_path_escaped}'",
                vcodec="h264_nvenc",
                acodec="aac",
                **{"rc:v": "vbr", "cq:v": "26", "preset": "p4", "maxrate:v": "2500k", "bufsize:v": "5000k"}
            )
            .overwrite_output()
            .run(quiet=False, cmd=r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
        )

        # Step 4: Upload to Supabase
        import os
        file_size_mb = os.path.getsize(final_clip_path) / (1024 * 1024)
        print(f"[DEBUG] Clip {idx} size: {file_size_mb:.2f} MB")

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
            "viral_score": int(round(float(moment.get("score", 0)))),
            "score_reason": moment.get("reason"),
            "storage_path": storage_path,
            "public_url": public_url
        }).execute()