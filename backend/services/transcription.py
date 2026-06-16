import json
import ffmpeg
import math
from pathlib import Path
from groq import Groq
from config import settings
from database import supabase
import time

_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def transcribe(video_path: str, job_id: str) -> list[dict]:
    """
    Extracts audio from video, transcribes via Groq Whisper API.
    Handles long videos by chunking audio into 10-minute segments.
    """
    tmp_dir = Path(settings.tmp_dir) / job_id
    audio_path = str(tmp_dir / "audio.wav")
    ffmpeg_bin = r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
    ffprobe_bin = r"C:\Users\ivylxvie\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"

    # Extract audio
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar=16000)
        .overwrite_output()
        .run(quiet=False, cmd=ffmpeg_bin)
    )

    # Get audio duration
    probe = ffmpeg.probe(audio_path, cmd=ffprobe_bin)
    duration = float(probe["format"]["duration"])
    print(f"[INFO] Audio duration: {duration:.1f}s")

    client = get_groq_client()
    chunk_duration = 600  # 10 minutes per chunk
    all_segments = []

    if duration <= chunk_duration:
        # Short video — transcribe directly
        segments = _transcribe_file(client, audio_path, 0)
        all_segments.extend(segments)
    else:
        # Long video — chunk into 10-minute pieces
        num_chunks = math.ceil(duration / chunk_duration)
        print(f"[INFO] Splitting into {num_chunks} chunks...")

        for i in range(num_chunks):
            chunk_start = i * chunk_duration
            chunk_duration_actual = min(chunk_duration, duration - chunk_start)
            chunk_path = str(tmp_dir / f"chunk_{i}.wav")

            (
                ffmpeg
                .input(audio_path, ss=chunk_start, t=chunk_duration_actual)
                .output(chunk_path)
                .overwrite_output()
                .run(quiet=True, cmd=ffmpeg_bin)
            )

            print(f"[INFO] Transcribing chunk {i+1}/{num_chunks}...")
            segments = _transcribe_file(client, chunk_path, chunk_start)
            all_segments.extend(segments)
            time.sleep(1)  # Rate limit buffer

    # Build transcript data
    all_words = [w for seg in all_segments for w in seg.get("words", [])]
    transcript_data = {"segments": all_segments, "words": all_words}

    # Save locally
    transcript_path_local = str(tmp_dir / "transcript.json")
    with open(transcript_path_local, "w") as f:
        json.dump(transcript_data, f)

    # Upload to Supabase with retry
    storage_path = f"transcripts/{job_id}.json"
    for attempt in range(3):
        try:
            with open(transcript_path_local, "rb") as f:
                supabase.storage.from_("clipos-assets").upload(
                    storage_path, f,
                    file_options={"upsert": "true"}
                )
            break
        except Exception as upload_err:
            if attempt == 2:
                raise
            time.sleep(3)

    supabase.table("jobs").update({"transcript_path": storage_path}).eq("id", job_id).execute()

    return all_segments


def _transcribe_file(client: Groq, audio_path: str, time_offset: float) -> list[dict]:
    """
    Transcribes a single audio file via Groq and returns segments
    with timestamps offset by time_offset seconds.
    """
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            language="en"
        )

    segments = []
    for seg in (response.segments or []):
        # Handle both dict and object response formats
        if isinstance(seg, dict):
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            seg_text = seg.get("text", "").strip()
            seg_words = seg.get("words", [])
        else:
            seg_start = seg.start
            seg_end = seg.end
            seg_text = seg.text.strip()
            seg_words = seg.words or []

        seg_data = {
            "start": round(seg_start + time_offset, 3),
            "end": round(seg_end + time_offset, 3),
            "text": seg_text,
            "words": []
        }

        for word in seg_words:
            if isinstance(word, dict):
                w_word = word.get("word", "").strip()
                w_start = word.get("start", 0)
                w_end = word.get("end", 0)
            else:
                w_word = word.word.strip()
                w_start = word.start
                w_end = word.end

            seg_data["words"].append({
                "word": w_word,
                "start": round(w_start + time_offset, 3),
                "end": round(w_end + time_offset, 3)
            })

        segments.append(seg_data)

    total_words = sum(len(s.get("words", [])) for s in segments)
    print(f"[DEBUG] Segments: {len(segments)}, Total words with timestamps: {total_words}")
    return segments