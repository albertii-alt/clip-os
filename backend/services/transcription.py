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
        full_segments.append(seg_data)

    # Flatten all words
    all_words = [w for seg in full_segments for w in seg["words"]]
    transcript_data = {"segments": full_segments, "words": all_words}

    # Save + upload to Supabase
    transcript_path_local = str(tmp_dir / "transcript.json")
    with open(transcript_path_local, "w") as f:
        json.dump(transcript_data, f)

    storage_path = f"transcripts/{job_id}.json"
    with open(transcript_path_local, "rb") as f:
        supabase.storage.from_("clipos-assets").upload(storage_path, f)

    supabase.table("jobs").update({"transcript_path": storage_path}).eq("id", job_id).execute()

    return full_segments