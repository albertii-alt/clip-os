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


def _clean(word: str) -> str:
    """Lowercase + strip punctuation for fuzzy matching."""
    return word.strip(".,!?;:\"'").lower()


def recover_orphan_words(segments: list[dict]) -> list[dict]:
    """
    For each segment, ensure every word in segment['text'] has a corresponding
    entry in segment['words'] with valid timestamps. Words missing timestamps
    (orphans) are inserted with interpolated start/end times.
    Returns the segments list with all words arrays complete and in order.
    """
    for seg in segments:
        seg_start  = seg.get("start", 0.0)
        seg_end    = seg.get("end",   0.0)
        text_words = seg.get("text", "").strip().split()
        ts_words   = seg.get("words", [])  # existing timestamped words

        if not text_words:
            continue

        # Build a lookup of clean->entry from existing timestamped words.
        # We walk through ts_words in order to handle repeated words correctly.
        ts_queue = list(ts_words)  # consumed left-to-right

        # First pass: align text_words against ts_queue by matching clean tokens.
        # Produce a list of (original_text_word, matched_entry_or_None).
        aligned: list[tuple[str, dict | None]] = []
        ts_idx = 0
        for tw in text_words:
            tw_clean = _clean(tw)
            # Look ahead in ts_queue for a match within a small window
            matched = None
            for lookahead in range(min(5, len(ts_queue) - ts_idx)):
                candidate = ts_queue[ts_idx + lookahead]
                if _clean(candidate["word"]) == tw_clean:
                    # consume everything up to and including this match
                    ts_idx += lookahead + 1
                    matched = candidate
                    break
            aligned.append((tw, matched))

        # Second pass: interpolate timestamps for orphans.
        # Find nearest anchored neighbor on each side.
        result: list[dict] = []
        n = len(aligned)
        for i, (tw, entry) in enumerate(aligned):
            if entry is not None:
                result.append(entry)
                continue

            # Find the nearest timestamped word before this orphan
            prev_end = seg_start
            for j in range(i - 1, -1, -1):
                if aligned[j][1] is not None:
                    prev_end = aligned[j][1]["end"]
                    break

            # Find the nearest timestamped word after this orphan
            next_start = seg_end
            for j in range(i + 1, n):
                if aligned[j][1] is not None:
                    next_start = aligned[j][1]["start"]
                    break

            # Count consecutive orphans in this gap to split time evenly
            gap_orphans = []
            for j in range(n):
                if aligned[j][1] is None:
                    # belongs to same gap if surrounded by same anchors
                    lo = seg_start
                    hi = seg_end
                    for k in range(j - 1, -1, -1):
                        if aligned[k][1] is not None:
                            lo = aligned[k][1]["end"]
                            break
                    for k in range(j + 1, n):
                        if aligned[k][1] is not None:
                            hi = aligned[k][1]["start"]
                            break
                    if lo == prev_end and hi == next_start:
                        gap_orphans.append(j)

            # Position of current orphan within its gap
            my_pos   = gap_orphans.index(i) if i in gap_orphans else 0
            gap_size = len(gap_orphans) if gap_orphans else 1
            slot     = (next_start - prev_end) / gap_size
            w_start  = round(prev_end + my_pos * slot, 3)
            w_end    = round(w_start + slot, 3)

            result.append({"word": tw, "start": w_start, "end": w_end})

        seg["words"] = result

    return segments


def _build_raw_chunks(
    words: list[dict],
    clip_start: float,
    clip_end: float,
) -> list[tuple[list[dict], float, float]]:
    """
    Core chunking logic. Returns list of (chunk_words, start_sec, end_sec)
    where chunk_words is the raw list of word dicts with their original timestamps.
    Overlap trimming is applied so no two chunks overlap.
    """
    EARLY_DISPLAY_MS = 0.05
    MIN_DISPLAY_SEC  = 0.3

    clip_words = [w for w in words if w["start"] >= clip_start and w["end"] <= clip_end]
    if not clip_words:
        return []

    chunk_size = 3
    raw: list[tuple[list[dict], float, float]] = []

    for chunk in [clip_words[i:i + chunk_size] for i in range(0, len(clip_words), chunk_size)]:
        if not chunk:
            continue
        start         = max(0.0, chunk[0]["start"] - clip_start - EARLY_DISPLAY_MS)
        last_word_end = chunk[-1]["end"] - clip_start
        # Cap at last_word_end + 0.3 — never stretch into post-speech silence.
        end           = max(start + MIN_DISPLAY_SEC, last_word_end + 0.3)
        raw.append((chunk, start, end))

    # Trim each chunk's end so it doesn't overlap the next chunk's start
    for i in range(len(raw) - 1):
        chunk_words, s, e = raw[i]
        next_s = raw[i + 1][1]
        if e > next_s:
            raw[i] = (chunk_words, s, next_s - 0.01)

    return raw


def compute_caption_chunks(
    words: list[dict],
    clip_start: float,
    clip_end: float,
    segments: list[dict] | None = None,
) -> list[tuple[str, float, float]]:
    """
    Returns a list of (text, start_sec, end_sec) tuples in clip-relative time.
    Shared by both the ASS writer and the drawtext generator.
    """
    result: list[tuple[str, float, float]] = []

    raw_chunks = _build_raw_chunks(words, clip_start, clip_end)
    if raw_chunks:
        for chunk_words, start, end in raw_chunks:
            text = " ".join(w["word"].upper() for w in chunk_words)
            result.append((text, start, end))

    elif segments:
        clip_segments = [s for s in segments if s["start"] >= clip_start and s["end"] <= clip_end]
        for seg in clip_segments:
            seg_duration = seg["end"] - seg["start"]
            text_lines   = chunk_text(seg["text"].upper().strip(), max_chars=20)
            if not text_lines:
                continue
            time_per_line = seg_duration / len(text_lines)
            for i, line_text in enumerate(text_lines):
                line_start = max(0.0, seg["start"] + (i * time_per_line) - clip_start)
                line_end   = line_start + time_per_line
                result.append((line_text, line_start, line_end))

    return result


def generate_ass_subtitles(
    words: list[dict],
    clip_start: float,
    clip_end: float,
    output_path: str,
    segments: list[dict] = None
):
    """
    Generates TikTok-style ASS subtitle file for a clip with karaoke word highlighting.
    Each spoken word turns yellow as it is said; the rest of the chunk stays white.
    Falls back to plain segment-level lines when no word timestamps are available.
    """
    # Two styles: Default (white, for unspoken words) and Highlight (yellow, for the active word).
    # \k tags are in centiseconds and control how long each word is "active" (highlighted).
    # Alignment 8 = top-center, so \pos y counts from the top — easier to reason about.
    # 860px from top on a 1920px canvas = ~45% down, just above center.
    CAPTION_Y = 950

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,8,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    raw_chunks = _build_raw_chunks(words, clip_start, clip_end)
    lines: list[str] = []

    if raw_chunks:
        for chunk_words, start, end in raw_chunks:
            t_start = seconds_to_ass_time(start)
            t_end   = seconds_to_ass_time(end)

            # \k<cs> = hard karaoke (instant colour switch, no fill sweep)
            # \1c sets the primary colour: yellow for the active word, white to reset.
            # ASS colour format is &HBBGGRR& (blue-green-red).
            # Yellow = &H00FFFF& (R=FF, G=FF, B=00), White = &HFFFFFF&
            parts: list[str] = []
            for w in chunk_words:
                duration_cs = max(1, round((w["end"] - w["start"]) * 100))
                label       = w["word"].upper()
                parts.append(f"{{\\k{duration_cs}}}{{\\1c&H00FFFF&}}{label}{{\\1c&HFFFFFF&}}")

            karaoke_text = f"{{\\pos(540,{CAPTION_Y})}}" + " ".join(parts)
            lines.append(
                f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{karaoke_text}"
            )

    elif segments:
        # Fallback: no word timestamps — plain segment lines, no highlighting
        plain_chunks = compute_caption_chunks([], clip_start, clip_end, segments)
        for t, s, e in plain_chunks:
            lines.append(
                f"Dialogue: 0,{seconds_to_ass_time(s)},{seconds_to_ass_time(e)},Default,,0,0,0,,{t}"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(lines))