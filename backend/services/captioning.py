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
    output_path: str,
    segments: list[dict] = None
):
    """
    Generates TikTok-style ASS subtitle file for a clip.
    Uses word-level timestamps if available, falls back to segment-level.
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

    # Try word-level first
    clip_words = [w for w in words if w["start"] >= clip_start and w["end"] <= clip_end]

    if clip_words:
        # Word-level subtitles — group into lines of 4 words
        chunk_size = 4
        for i in range(0, len(clip_words), chunk_size):
            chunk = clip_words[i:i + chunk_size]
            if not chunk:
                continue
            start_ts = seconds_to_ass_time(chunk[0]["start"] - clip_start)
            end_ts = seconds_to_ass_time(chunk[-1]["end"] - clip_start)
            text = " ".join(w["word"].upper() for w in chunk)
            lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")

    elif segments:
        # Fallback — segment-level subtitles
        clip_segments = [
            s for s in segments
            if s["start"] >= clip_start and s["end"] <= clip_end
        ]
        for seg in clip_segments:
            start_ts = seconds_to_ass_time(seg["start"] - clip_start)
            end_ts = seconds_to_ass_time(seg["end"] - clip_start)
            # Break long text into chunks of ~40 chars
            text = seg["text"].upper().strip()
            lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(lines))