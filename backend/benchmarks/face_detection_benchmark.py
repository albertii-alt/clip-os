"""
MediaPipe Face Detection Benchmark (Tasks API)
===============================================
Standalone diagnostic script — does NOT touch the pipeline.
Fill in SAMPLE_VIDEO_PATH before running.

Run with:
    python backend/benchmarks/face_detection_benchmark.py
"""

import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ── CONFIG ────────────────────────────────────────────────────────────────────
SAMPLE_VIDEO_PATH = r"C:\Users\ivylxvie\Downloads\Hailey Bieber Opens Up About Motherhood, Fame and Her $1 Billion Brand - TIME (1080p).mp4"
SAMPLE_RATE_FPS   = 2
MAX_VIDEO_SECONDS = 60

MODEL_PATH = Path(__file__).parent / "blaze_face_short_range.tflite"
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
# ─────────────────────────────────────────────────────────────────────────────


def ensure_model():
    if not MODEL_PATH.exists():
        print(f"  Downloading model to {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("  Download complete.")


def run_benchmark():
    print()
    print("=" * 60)
    print("  MediaPipe Face Detection Benchmark")
    print("=" * 60)
    print(f"  Video  : {SAMPLE_VIDEO_PATH}")
    print(f"  Sample : {SAMPLE_RATE_FPS} fps")
    print(f"  Max    : first {MAX_VIDEO_SECONDS}s of video")
    print("=" * 60)
    print()

    ensure_model()

    cap = cv2.VideoCapture(SAMPLE_VIDEO_PATH)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {SAMPLE_VIDEO_PATH}")
        return

    video_fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_skip   = max(1, round(video_fps / SAMPLE_RATE_FPS))
    max_frames   = int(MAX_VIDEO_SECONDS * video_fps)

    print(f"  Video FPS      : {video_fps:.2f}")
    print(f"  Total frames   : {total_frames}")
    print(f"  Frame skip     : every {frame_skip} frames (~{SAMPLE_RATE_FPS} fps sample)")
    print(f"  Processing up to frame {min(total_frames, max_frames)}")
    print()

    detection_times: list[float] = []
    face_centers:    list[tuple[float, float] | None] = []

    base_options    = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
    detector_options = mp_vision.FaceDetectorOptions(base_options=base_options)
    detector        = mp_vision.FaceDetector.create_from_options(detector_options)

    frame_idx     = 0
    sampled_count = 0

    with detector:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx > max_frames:
                break

            if frame_idx % frame_skip == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                t_start = time.perf_counter()
                results = detector.detect(mp_image)
                t_end   = time.perf_counter()

                elapsed_ms = (t_end - t_start) * 1000
                detection_times.append(elapsed_ms)

                if results.detections:
                    det  = results.detections[0]
                    bbox = det.bounding_box
                    cx   = (bbox.origin_x + bbox.width  / 2)
                    cy   = (bbox.origin_y + bbox.height / 2)
                    face_centers.append((cx, cy))
                else:
                    face_centers.append(None)

                sampled_count += 1

            frame_idx += 1

    cap.release()

    if not detection_times:
        print("[ERROR] No frames were processed.")
        return

    faces_found  = sum(1 for c in face_centers if c is not None)
    faces_missed = sampled_count - faces_found
    avg_ms       = sum(detection_times) / len(detection_times)
    min_ms       = min(detection_times)
    max_ms       = max(detection_times)
    total_ms     = sum(detection_times)

    typical_clip_seconds = 50
    typical_frames       = typical_clip_seconds * SAMPLE_RATE_FPS
    estimated_ms         = avg_ms * typical_frames

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Frames sampled          : {sampled_count}")
    print(f"  Faces detected          : {faces_found}  ({faces_found/sampled_count*100:.1f}%)")
    print(f"  No face found           : {faces_missed}  ({faces_missed/sampled_count*100:.1f}%)")
    print()
    print(f"  Avg detection time      : {avg_ms:.2f} ms")
    print(f"  Min detection time      : {min_ms:.2f} ms")
    print(f"  Max detection time      : {max_ms:.2f} ms")
    print(f"  Total detection time    : {total_ms:.2f} ms  ({total_ms/1000:.2f}s)")
    print()
    print(f"  Estimated time for 50s clip")
    print(f"  ({typical_frames} frames @ {avg_ms:.2f}ms each)")
    print(f"  → {estimated_ms:.0f} ms  ({estimated_ms/1000:.2f}s)")
    print("=" * 60)
    print()


if __name__ == "__main__":
    run_benchmark()
