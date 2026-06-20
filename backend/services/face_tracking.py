"""
Face tracking service — dynamic horizontal crop positioning via MediaPipe.
Uses the legacy mp.solutions.face_detection API which has no telemetry/network calls.
"""

import os
os.environ["GLOG_minloglevel"] = "2"

import cv2
import mediapipe as mp


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
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    video_fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_skip  = max(1, round(video_fps / sample_fps))
    start_frame = int(start * video_fps)
    end_frame   = int(end   * video_fps)

    results: list[tuple[float, float | None]] = []
    frame_idx = start_frame

    with mp.solutions.face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5
    ) as detector:
        while frame_idx <= end_frame:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            rgb        = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            det_result = detector.process(rgb)
            timestamp  = (frame_idx - start_frame) / video_fps

            if det_result.detections:
                bbox   = det_result.detections[0].location_data.relative_bounding_box
                norm_x = bbox.xmin + bbox.width / 2
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
    # Uses gte(t,t0)*lte(t,t1) instead of between(t,t0,t1) to avoid commas
    # inside the expression — ffmpeg-python's vf= quoting does not reliably
    # preserve \, escapes, causing bare floats to appear as filter tokens.
    def make_lerp(px0: int, px1: int, t0: float, t1: float) -> str:
        dt = t1 - t0
        if dt <= 0 or px0 == px1:
            return str(px0)
        return f"({px0}+({px1}-{px0})*(t-{t0:.4f})/{dt:.4f})"

    def make_cond(t0: float, t1: float) -> str:
        # gte(t,t0)*lte(t,t1) == 1 only when t0 <= t <= t1, no commas needed
        return f"gte(t\\,{t0:.4f})*lte(t\\,{t1:.4f})"

    px_values = [norm_to_px(nx) for _, nx in positions]
    px_final  = px_values[-1]

    # Start from the last segment as the fallback and wrap inward.
    expr = str(px_final)
    for i in reversed(range(len(positions) - 1)):
        t0  = positions[i][0]
        t1  = positions[i + 1][0]
        px0 = px_values[i]
        px1 = px_values[i + 1]
        if t1 - t0 <= 0:
            continue
        lerp = make_lerp(px0, px1, t0, t1)
        cond = make_cond(t0, t1)
        # if(cond, lerp, fallback) — commas here are inside if() so must be \,
        expr = f"if({cond}\\,{lerp}\\,{expr})"

    return f"crop={target_width}:{target_height}:{expr}:0"
