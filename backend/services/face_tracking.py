"""
Face tracking service — dynamic horizontal crop positioning.
Uses OpenCV's built-in Haar cascade detector (haarcascade_frontalface_default.xml).
No MediaPipe, no telemetry, no network calls, no external model downloads.
"""

import cv2


def detect_face_positions(
    video_path: str,
    start: float,
    end: float,
    sample_fps: float = 1.0,
) -> list[tuple[float, float | None]]:
    """
    Sample frames from [start, end] at sample_fps and detect the face horizontal center.
    Returns list of (timestamp_relative_to_start, normalized_x | None).
    normalized_x is face center x as fraction of frame width (0.0–1.0).
    """
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    video_fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_skip  = max(1, round(video_fps / sample_fps))
    start_frame = int(start * video_fps)
    end_frame   = int(end   * video_fps)

    results: list[tuple[float, float | None]] = []

    # Seek once to start_frame, then read sequentially — much faster than
    # repeated random seeks in compressed MP4 which force keyframe decoding.
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_idx = start_frame

    while frame_idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        # Only process frames at the desired sample interval
        if (frame_idx - start_frame) % frame_skip == 0:
            w         = frame.shape[1]
            gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces     = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            timestamp = (frame_idx - start_frame) / video_fps

            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                norm_x = (x + fw / 2) / w
                results.append((timestamp, max(0.0, min(1.0, norm_x))))
            else:
                results.append((timestamp, None))

        frame_idx += 1

    cap.release()
    return results


def fill_gaps_and_smooth(
    positions: list[tuple[float, float | None]],
    max_px_delta: int = 80,
    orig_width: int = 1920,
    target_width: int = 1080,
) -> list[tuple[float, float]]:
    """
    Forward-fill None gaps, apply a 15-sample moving average, then clamp
    the maximum pixel jump between consecutive keyframes to max_px_delta.
    Larger window and delta clamp prevent jittery Haar cascade detections
    from causing visible panning in the output.
    """
    if not positions:
        return []

    # Forward-fill None values
    last_known = 0.5
    filled: list[tuple[float, float]] = []
    for ts, x in positions:
        if x is not None:
            last_known = x
        filled.append((ts, last_known))

    # Larger window = more temporal smoothing (15 samples @ 1fps = 15s)
    window = 15
    xs = [x for _, x in filled]
    smoothed: list[tuple[float, float]] = []
    for i, (ts, _) in enumerate(filled):
        lo  = max(0, i - window // 2)
        hi  = min(len(xs), lo + window)
        avg = sum(xs[lo:hi]) / (hi - lo)
        smoothed.append((ts, avg))

    # Clamp max pixel jump between consecutive samples to suppress rapid pans.
    # Convert norm_x delta to pixels, clamp, convert back.
    max_x     = max(1, orig_width - target_width)
    max_delta = max_px_delta / orig_width  # normalised delta threshold

    clamped: list[tuple[float, float]] = [smoothed[0]]
    for i in range(1, len(smoothed)):
        ts, nx   = smoothed[i]
        prev_nx  = clamped[-1][1]
        delta    = nx - prev_nx
        if abs(delta) > max_delta:
            nx = prev_nx + max_delta * (1 if delta > 0 else -1)
        clamped.append((ts, max(0.0, min(1.0, nx))))

    return clamped


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

    deduped: list[tuple[float, float]] = [positions[0]]
    for ts, nx in positions[1:]:
        if norm_to_px(nx) != norm_to_px(deduped[-1][1]):
            deduped.append((ts, nx))
    positions = deduped

    if len(positions) == 1:
        return f"crop={target_width}:{target_height}:{norm_to_px(positions[0][1])}:0"

    if len(positions) > 48:
        step = len(positions) / 48
        positions = [positions[int(i * step)] for i in range(48)] + [positions[-1]]

    def make_lerp(px0: int, px1: int, t0: float, t1: float) -> str:
        dt = t1 - t0
        if dt <= 0 or px0 == px1:
            return str(px0)
        return f"({px0}+({px1}-{px0})*(t-{t0:.4f})/{dt:.4f})"

    def make_cond(t0: float, t1: float) -> str:
        return f"gte(t\\,{t0:.4f})*lte(t\\,{t1:.4f})"

    px_values = [norm_to_px(nx) for _, nx in positions]
    px_final  = px_values[-1]

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
        expr = f"if({cond}\\,{lerp}\\,{expr})"

    return f"crop={target_width}:{target_height}:{expr}:0"
