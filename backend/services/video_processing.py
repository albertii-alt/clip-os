import json
import os
import shutil
import time
import uuid
import ffmpeg
from pathlib import Path
from config import settings
from database import supabase
from services.captioning import generate_ass_subtitles, compute_caption_chunks, debug_find_orphan_words
from services.face_tracking import (
    detect_face_positions,
    fill_gaps_and_smooth,
    build_dynamic_crop_filter,
)


FFMPEG_BIN  = r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE_BIN = r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

FONT_PATHS = {
    "arial":   {"bold": r"C:\Windows\Fonts\arialbd.ttf",  "regular": r"C:\Windows\Fonts\arial.ttf"},
    "impact":  {"bold": r"C:\Windows\Fonts\impact.ttf",   "regular": r"C:\Windows\Fonts\impact.ttf"},
    "segoe":   {"bold": r"C:\Windows\Fonts\segoeuib.ttf", "regular": r"C:\Windows\Fonts\segoeui.ttf"},
    "calibri": {"bold": r"C:\Windows\Fonts\calibrib.ttf", "regular": r"C:\Windows\Fonts\calibri.ttf"},
}

# Suppress FFmpeg Fontconfig error spam on Windows
os.environ.setdefault("FC_CONFIG_FILE", "")
os.environ.setdefault("FONTCONFIG_FILE", "")


def _get_crop_filter(
    raw_clip_path: str,
    orig_width: int,
    orig_height: int,
    target_w: int,
    target_h: int,
    clip_duration: float,
    clip_idx: int,
) -> str:
    """Run face tracking and return a crop filter string, with static fallback."""
    _ft_start = time.perf_counter()
    try:
        raw_positions = detect_face_positions(raw_clip_path, 0.0, clip_duration)
        smoothed      = fill_gaps_and_smooth(raw_positions)
        if not smoothed:
            raise ValueError("no usable positions")
        crop_filter = build_dynamic_crop_filter(
            smoothed, orig_width, orig_height, target_w, target_h, clip_duration
        )
    except Exception as e:
        print(f"[WARN] Face tracking failed for clip {clip_idx} ({e}) — falling back to static center-crop")
        static_x    = max(0, (orig_width - target_w) // 2)
        crop_filter = f"crop={target_w}:{target_h}:{static_x}:0"
    _ft_ms = (time.perf_counter() - _ft_start) * 1000
    print(f"[INFO] Face tracking took {_ft_ms:.1f}ms for clip {clip_idx}")
    return crop_filter


def render_boxed_clip(
    raw_clip_path: str,
    final_clip_path: str,
    orig_width: int,
    orig_height: int,
    clip_duration: float,
    clip_idx: int,
    transcript: dict,
    clip_start: float,
    clip_end: float,
    short_title: str,
    bg_color: str,
    font_choice: str = 'arial',
) -> None:
    """
    Boxed layout:
      - 1080x1080 square (face-tracked crop) centered on 1080x1920 canvas
      - short_title drawn in top zone (above square)
      - word-by-word captions drawn in bottom zone (below square)
      - GPU encode with same settings as full_bleed path
    Canvas: 1080 wide x 1920 tall
    Square: 1080x1080, starts at y=420 (leaving 420px top + 420px bottom)
    """
    CANVAS_W    = 1080
    CANVAS_H    = 1920
    SQUARE_SIZE = 1080
    SQUARE_Y    = (CANVAS_H - SQUARE_SIZE) // 2  # 420

    text_color  = "white" if bg_color == "black" else "black"
    pad_color   = bg_color

    # Resolve font paths
    font_set     = FONT_PATHS.get(font_choice, FONT_PATHS["arial"])
    title_font   = font_set["bold"]
    caption_font = font_set["regular"]

    # ── Face-tracked square crop ──────────────────────────────────────────────
    crop_filter = _get_crop_filter(
        raw_clip_path, orig_width, orig_height,
        SQUARE_SIZE, SQUARE_SIZE,
        clip_duration, clip_idx,
    )

    # ── Build caption drawtext segments ──────────────────────────────────────
    caption_y   = SQUARE_Y + SQUARE_SIZE + 30  # 30px below square
    chunks      = compute_caption_chunks(
        transcript["words"], clip_start, clip_end,
        segments=transcript.get("segments", [])
    )

    def esc(s: str) -> str:
        """Escape text content for FFmpeg drawtext filter.
        Order matters: backslash must be escaped first.
        Single quotes replaced with backtick - ASCII, universally renderable,
        no special meaning to FFmpeg's filter parser.
        """
        return (
            s.replace("\\", "\\\\")  # \ → \\ (must be first)
             .replace("'", "`")      # ' → ` (ASCII substitute, always renders)
             .replace(":", "\\:")    # : → \: (key=value separator)
             .replace("%", "\\%")    # % → \% (strftime expansion)
             .replace(",", "\\,")    # , → \, (filter chain separator)
             .replace("[", "\\[")    # [ → \[ (filter graph label)
             .replace("]", "\\]")
        )

    def esc_path(path: str) -> str:
        """Escape a Windows file path for use as an FFmpeg filter option value."""
        return path.replace("\\", "/").replace(":", "\\:")

    caption_filters = ""
    for text, t_start, t_end in chunks:
        caption_filters += (
            f",drawtext=text='{esc(text)}'"
            f":fontfile='{esc_path(caption_font)}':fontsize=58:fontcolor={text_color}"
            f":x=(w-text_w)/2:y={caption_y}"
            f":enable='gte(t,{t_start:.3f})*lte(t,{t_end:.3f})'"
        )

    # ── Short title drawtext (tight above square) ───────────────────────────────
    TITLE_GAP = 25   # px between title box bottom and square top
    title_y   = max(20, SQUARE_Y - TITLE_GAP - 70)
    title_escaped = esc(short_title.upper())
    title_filter  = (
        f",drawtext=text='{title_escaped}'"
        f":fontfile='{esc_path(title_font)}':fontsize=48:fontcolor=black:fix_bounds=1:text_shaping=0"
        f":x=(w-text_w)/2:y={title_y}"
        f":box=1:boxcolor=white@0.92:boxborderw=16"
    )

    # ── Full filter chain ─────────────────────────────────────────────────────
    # crop square → pad to 1080x1920 → title → captions
    full_vf = (
        f"{crop_filter},scale={SQUARE_SIZE}:{SQUARE_SIZE},"
        f"pad={CANVAS_W}:{CANVAS_H}:(ow-iw)/2:{SQUARE_Y}:color={pad_color}"
        f"{title_filter}"
        f"{caption_filters}"
    )
    print(f"[DEBUG] boxed vf for clip {clip_idx}: {full_vf[:160]}{'...' if len(full_vf) > 160 else ''}")
    print(f"[DEBUG] full_vf: {full_vf}")

    (
        ffmpeg
        .input(raw_clip_path)
        .output(
            final_clip_path,
            vf=full_vf,
            vcodec="h264_nvenc",
            acodec="aac",
            **{"rc:v": "vbr", "cq:v": "26", "preset": "p4", "maxrate:v": "2500k", "bufsize:v": "5000k"}
        )
        .overwrite_output()
        .run(quiet=False, cmd=FFMPEG_BIN)
    )


def render_clips(video_path: str, moments: list[dict], job_id: str, campaign: dict | None = None, layout_style: str = 'full_bleed', bg_color: str = 'black', font_choice: str = 'arial'):
    """
    For each moment: cut → reframe to 9:16 → burn captions → upload to Supabase.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    clips_dir = tmp_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Get video dimensions
    probe = ffmpeg.probe(video_path, cmd=FFPROBE_BIN)
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

    # Diagnostic: log any words in segment text with no timestamp entry
    debug_find_orphan_words(transcript.get("segments", []))

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
        start    = moment["start_seconds"]
        end      = moment["end_seconds"]
        duration = end - start
        clip_id  = str(uuid.uuid4())

        raw_clip_path   = str(clips_dir / f"raw_{idx}.mp4")
        final_clip_path = str(clips_dir / f"clip_{idx}.mp4")

        # Step 1: Cut raw clip
        (
            ffmpeg
            .input(video_path, ss=start, t=duration)
            .output(raw_clip_path, c="copy")
            .overwrite_output()
            .run(quiet=False, cmd=FFMPEG_BIN)
        )

        if layout_style == 'boxed':
            # Step 2+3: Boxed layout — square + padded canvas + drawtext captions
            short_title = moment.get("short_title") or moment.get("hook") or ""
            render_boxed_clip(
                raw_clip_path=raw_clip_path,
                final_clip_path=final_clip_path,
                orig_width=orig_width,
                orig_height=orig_height,
                clip_duration=duration,
                clip_idx=idx,
                transcript=transcript,
                clip_start=start,
                clip_end=end,
                short_title=short_title,
                bg_color=bg_color,
                font_choice=font_choice,
            )
        else:
            # Step 2: Generate ASS captions (full_bleed path)
            ass_path         = str(clips_dir / f"clip_{idx}.ass")
            ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
            generate_ass_subtitles(
                transcript["words"],
                start,
                end,
                ass_path,
                segments=transcript.get("segments", [])
            )

            # Step 3: Face-tracked crop → scale 1080x1920 → ASS subtitles
            target_h    = orig_height
            target_w    = int(orig_height * 9 / 16)
            crop_filter = _get_crop_filter(
                raw_clip_path, orig_width, orig_height,
                target_w, target_h, duration, idx
            )
            full_vf = f"{crop_filter},scale=1080:1920,subtitles='{ass_path_escaped}'"
            print(f"[DEBUG] vf filter for clip {idx}: {full_vf[:120]}{'...' if len(full_vf) > 120 else ''}")

            (
                ffmpeg
                .input(raw_clip_path)
                .output(
                    final_clip_path,
                    vf=full_vf,
                    vcodec="h264_nvenc",
                    acodec="aac",
                    **{"rc:v": "vbr", "cq:v": "26", "preset": "p4", "maxrate:v": "2500k", "bufsize:v": "5000k"}
                )
                .overwrite_output()
                .run(quiet=False, cmd=FFMPEG_BIN)
            )

        # Step 4: Move clip to permanent local storage
        file_size_mb = os.path.getsize(final_clip_path) / (1024 * 1024)
        print(f"[DEBUG] Clip {idx} size: {file_size_mb:.2f} MB")

        clip_dest_dir = os.path.join(settings.clips_dir, job_id)
        os.makedirs(clip_dest_dir, exist_ok=True)
        dest_path = os.path.join(clip_dest_dir, f"clip_{idx}.mp4")
        shutil.move(final_clip_path, dest_path)

        storage_path = dest_path
        public_url   = f"http://localhost:8000/clips/{job_id}/clip_{idx}.mp4"

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