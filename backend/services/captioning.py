def seconds_to_ass_time(s: float) -> str:
    """Convert float seconds to ASS timestamp format H:MM:SS.cc"""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{int(sec):02d}.{cs:02d}"


def chunk_text(text: str, max_chars: int = 20) -> list[str]:
    """
    Break text into short lines of max_chars characters.
    Tries to break at word boundaries.
    """
    words = text.split()
    lines = []
    current_line = []
    current_len = 0

    for word in words:
        if current_len + len(word) + 1 > max_chars and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)
        else:
            current_line.append(word)
            current_len += len(word) + 1

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def generate_ass_subtitles(
    words: list[dict],
    clip_start: float,
    clip_end: float,
    output_path: str,
    segments: list[dict] = None
):
    """
    Generates TikTok-style ASS subtitle file for a clip.
    - Position: lower center (70% down)
    - Max 3 words per line
    - Short punchy display
    """
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Style explanation:
    # Alignment=2 means bottom-center
    # MarginV=300 means 300px from bottom (avoids TikTok UI)
    # Shadow=2 adds drop shadow for readability
    # Spacing=2 adds letter spacing

    lines = []
    clip_words = [w for w in words if w["start"] >= clip_start and w["end"] <= clip_end]

    EARLY_DISPLAY_MS = 0.05   # Show caption 50ms before word is spoken
    MIN_DISPLAY_SEC = 0.3     # Each subtitle shows for at least 300ms

    if clip_words:
        chunk_size = 3
        chunks = [clip_words[i:i + chunk_size] for i in range(0, len(clip_words), chunk_size)]

        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue

            # Start 50ms early so viewer reads before hearing
            raw_start = chunk[0]["start"] - clip_start - EARLY_DISPLAY_MS
            start = max(0.0, raw_start)

            # End when next chunk starts (or last word ends + small buffer)
            if idx + 1 < len(chunks):
                next_chunk_start = chunks[idx + 1][0]["start"] - clip_start - EARLY_DISPLAY_MS
                end = max(start + MIN_DISPLAY_SEC, next_chunk_start)
            else:
                end = chunk[-1]["end"] - clip_start + 0.3

            # Never overlap with next chunk
            end = min(end, clip_end - clip_start)

            start_ts = seconds_to_ass_time(start)
            end_ts = seconds_to_ass_time(end)
            text = " ".join(w["word"].upper() for w in chunk)
            lines.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
            )

    elif segments:
        # Segment fallback — break long segments into short timed lines
        clip_segments = [
            s for s in segments
            if s["start"] >= clip_start and s["end"] <= clip_end
        ]
        for seg in clip_segments:
            seg_duration = seg["end"] - seg["start"]
            text_lines = chunk_text(seg["text"].upper().strip(), max_chars=20)
            if not text_lines:
                continue

            # Distribute time evenly across lines
            time_per_line = seg_duration / len(text_lines)
            for i, line_text in enumerate(text_lines):
                line_start = seg["start"] + (i * time_per_line) - clip_start
                line_end = line_start + time_per_line
                if line_start < 0:
                    line_start = 0
                start_ts = seconds_to_ass_time(line_start)
                end_ts = seconds_to_ass_time(line_end)
                lines.append(
                    f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{line_text}"
                )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(lines))