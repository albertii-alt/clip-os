"""
Face tracking service — dynamic horizontal crop positioning via MediaPipe.
"""

import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_PATH = Path(__file__).parent.parent / "benchmarks" / "blaze_face_short_range.tflite"
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"


def _ensure_model() -> None:
    if not MODEL_PATH.exists():
        print(f"[INFO] Downloading face detection model to {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[INFO] Model download complete.")


def detect_face_positions(
    video_path: str,
    start: float,
    end: float,
    sample_fps: float = 2.0,
) -> list[tuple[float, float | None]]:
    """
    Sample frames from [start, end] at sample_fps and detect the face horizontal center.
    Returns list of (timestamp_relative_to_start, normalized_x | None).
    normalized_x is face center x as fraction of frame width (0.0–1.0).
    """
    _ensure_model()

    base_options     = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
    detector_options = mp_vision.FaceDetectorOptions(base_options=base_options)
    detector         = mp_vision.FaceDetector.create_from_options(detector_options)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    video_fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_skip  = max(1, round(video_fps / sample_fps))
    start_frame = int(start * video_fps)
    end_frame   = int(end   * video_fps)

    results: list[tuple[float, float | None]] = []
    frame_idx = start_frame

    with detector:
        while frame_idx <= end_frame:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            w          = frame.shape[1]
            rgb        = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            det_result = detector.detect(mp_image)
            timestamp  = (frame_idx - start_frame) / video_fps

            if det_result.detections:
                bbox   = det_result.detections[0].bounding_box
                norm_x = (bbox.origin_x + bbox.width / 2) / w
                results.append((timestamp, max(0.0, min(1.0, norm_x))))
            else:
                results.append((timestamp, None))

            frame_idx += frame_skip

    cap.release()
    return results


def fill_gaps_and_smooth(
    positions: list[tuple[float, float | None]],
) -> list[tuple[float, float]]:
    """
    Forward-fill None gaps, then apply a 7-sample moving average.
    If the list starts with None, uses 0.5 (center) as initial fallback.
    """
    if not positions:
        return []

    # Forward-fill
    last_known = 0.5
    filled: list[tuple[float, float]] = []
    for ts, x in positions:
        if x is not None:
            last_known = x
        filled.append((ts, last_known))

    # Moving average (window=7 @ 2fps = 3.5s of smoothing)
    window = 7
    xs = [x for _, x in filled]
    smoothed: list[tuple[float, float]] = []
    for i, (ts, _) in enumerate(filled):
        lo = max(0, i - window // 2)
        hi = min(len(xs), lo + window)
        avg = sum(xs[lo:hi]) / (hi - lo)
        smoothed.append((ts, avg))

    return smoothed


def build_dynamic_crop_filter(
    positions: list[tuple[float, float]],
    orig_width: int,
    orig_height: int,
    target_width: int,
    target_height: int,
    clip_duration: float,
) -> str:
    """
    Build an FFmpeg crop filter string where x-offset varies with time.
    Falls back to static center-crop if orig_width <= target_width.
    """
    if orig_width <= target_width:
        static_x = max(0, (orig_width - target_width) // 2)
        return f"crop={target_width}:{target_height}:{static_x}:0"

    max_x = orig_width - target_width

    def norm_to_px(norm_x: float) -> int:
        raw = norm_x * orig_width - target_width / 2
        return int(max(0, min(max_x, raw)))

    if not positions:
        return f"crop={target_width}:{target_height}:{max_x // 2}:0"

    # Deduplicate consecutive identical pixel values — a 60s clip at 2fps
    # produces 120 keyframes; if the face barely moves they all map to the same
    # pixel, collapsing to a single static crop and avoiding deep nesting.
    deduped: list[tuple[float, float]] = [positions[0]]
    for ts, nx in positions[1:]:
        if norm_to_px(nx) != norm_to_px(deduped[-1][1]):
            deduped.append((ts, nx))
    positions = deduped

    if len(positions) == 1:
        return f"crop={target_width}:{target_height}:{norm_to_px(positions[0][1])}:0"

    # Cap at 48 unique keyframes so the nested if/between expression stays well
    # under FFmpeg's evaluator recursion limit.
    if len(positions) > 48:
        step = len(positions) / 48
        positions = [positions[int(i * step)] for i in range(48)] + [positions[-1]]

    # Build a linearly-interpolating expression between consecutive keyframes.
    # For each segment [t0, t1] the x offset glides from px0 to px1 using:
    #   lerp(px0, px1, (t - t0) / (t1 - t0))
    # which equals:  px0 + (px1 - px0) * (t - t0) / (t1 - t0)
    #
    # Commas inside expressions must be escaped as \, — FFmpeg's filter chain
    # parser splits on bare commas even when args are a subprocess list.
    def C(v: str) -> str:
        """Escape a comma for use inside an FFmpeg filter expression."""
        return v.replace(",", "\\,")

    px_values = [norm_to_px(nx) for _, nx in positions]
    px_final  = px_values[-1]

    # Start from the last segment as the fallback and wrap inward.
    expr = str(px_final)
    for i in reversed(range(len(positions) - 1)):
        t0  = positions[i][0]
        t1  = positions[i + 1][0]
        px0 = px_values[i]
        px1 = px_values[i + 1]
        dt  = t1 - t0
        if dt <= 0:
            continue
        # Linear interpolation: px0 + (px1-px0) * (t-t0)/dt
        # Written as an FFmpeg expression with escaped commas.
        frac = C(f"(t-{t0:.4f})/{dt:.4f}")
        lerp = C(f"{px0}+({px1}-{px0})*{frac}")
        cond = C(f"between(t,{t0:.4f},{t1:.4f})")
        expr = f"if({cond}\\,{lerp}\\,{expr})"

    return f"crop={target_width}:{target_height}:{expr}:0"
