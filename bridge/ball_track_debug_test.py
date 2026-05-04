#!/usr/bin/env python3

import cv2
import numpy as np
import time
from collections import deque

# =========================
# Camera settings
# =========================
DEVICE = 0
WIDTH = 640
HEIGHT = 480
FPS = 30
DURATION = 0          # 0 = run forever
USE_MJPG = True
NO_DISPLAY = False    # True = terminal only, False = show windows

# =========================
# Ball tracking parameters
# Tuned narrower for bright cyan / turquoise ball
# =========================
HUE_LOW = 90
HUE_HIGH = 106
SAT_LOW = 100
SAT_HIGH = 220
VAL_LOW = 100
VAL_HIGH = 255

MIN_RADIUS = 8
BLUR_KERNEL = 2
ERODE_ITER = 0
DILATE_ITER = 1

# =========================
# Shape filters
# =========================
MIN_CIRCULARITY = 0.72
MIN_FILL_RATIO = 0.60
MAX_ASPECT_ERROR = 0.30


def fourcc_to_str(value):
    value = int(value)
    return "".join(chr((value >> 8 * i) & 0xFF) for i in range(4))


def print_camera_state(cap, label):
    print(f"\n=== {label} ===")
    try:
        print("backend:", cap.getBackendName())
    except Exception:
        pass

    print("width: ", cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    print("height:", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("fps:   ", cap.get(cv2.CAP_PROP_FPS))
    print("fourcc:", repr(fourcc_to_str(cap.get(cv2.CAP_PROP_FOURCC))))


def set_prop(cap, prop, value, name):
    ok = cap.set(prop, value)
    readback = cap.get(prop)

    if prop == cv2.CAP_PROP_FOURCC:
        requested = fourcc_to_str(value)
        actual = fourcc_to_str(readback)
    else:
        requested = value
        actual = readback

    print(f"set {name:>8}: requested={requested!r}, ok={ok}, readback={actual!r}")


def track_ball(frame):
    # Keep your current behavior: BLUR_KERNEL=2 becomes 3 because Gaussian needs odd kernel.
    k = BLUR_KERNEL if BLUR_KERNEL % 2 == 1 else BLUR_KERNEL + 1

    if BLUR_KERNEL > 1:
        blurred = cv2.GaussianBlur(frame, (k, k), 0)
    else:
        blurred = frame

    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    lower = np.array([HUE_LOW, SAT_LOW, VAL_LOW], dtype=np.uint8)
    upper = np.array([HUE_HIGH, SAT_HIGH, VAL_HIGH], dtype=np.uint8)

    mask = cv2.inRange(hsv, lower, upper)

    if ERODE_ITER > 0:
        mask = cv2.erode(mask, None, iterations=ERODE_ITER)

    if DILATE_ITER > 0:
        mask = cv2.dilate(mask, None, iterations=DILATE_ITER)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(cnts) == 0:
        return "none", None, mask

    # Check candidates largest first, but do not blindly accept the largest.
    # This prevents a large same-color rectangle from winning automatically.
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for c in cnts:
        area = cv2.contourArea(c)
        if area <= 0:
            continue

        ((cx, cy), radius) = cv2.minEnclosingCircle(c)

        if radius < MIN_RADIUS:
            continue

        x, y, w, h = cv2.boundingRect(c)

        # Check 1: bounding box should be roughly square.
        aspect = w / float(h) if h > 0 else 999.0
        aspect_error = abs(1.0 - aspect)

        if aspect_error > MAX_ASPECT_ERROR:
            continue

        # Check 2: contour should be circle-like.
        # Perfect circle is close to 1.0.
        perimeter = cv2.arcLength(c, True)
        if perimeter <= 0:
            continue

        circularity = 4.0 * np.pi * area / (perimeter * perimeter)

        if circularity < MIN_CIRCULARITY:
            continue

        # Check 3: contour should fill its enclosing circle reasonably well.
        circle_area = np.pi * radius * radius
        fill_ratio = area / circle_area if circle_area > 0 else 0.0

        if fill_ratio < MIN_FILL_RATIO:
            continue

        cx, cy = int(cx), int(cy)

        result = f"{cx},{cy},{x},{y},{w},{h}"

        detection = {
            "cx": cx,
            "cy": cy,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "radius": radius,
            "area": area,
            "circularity": circularity,
            "fill_ratio": fill_ratio,
            "aspect": aspect,
            "aspect_error": aspect_error,
            "contour": c,
        }

        return result, detection, mask

    return "none", None, mask


print(f"Opening camera {DEVICE}...")

cap = cv2.VideoCapture(DEVICE)

if not cap.isOpened():
    raise RuntimeError("Could not open camera")

print_camera_state(cap, "Initial camera state")

print("\nApplying requested camera settings...")

if USE_MJPG:
    set_prop(cap, cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"), "FOURCC")

set_prop(cap, cv2.CAP_PROP_FRAME_WIDTH, WIDTH, "WIDTH")
set_prop(cap, cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT, "HEIGHT")
set_prop(cap, cv2.CAP_PROP_FPS, FPS, "FPS")
set_prop(cap, cv2.CAP_PROP_BUFFERSIZE, 1, "BUFFER")

print_camera_state(cap, "Actual camera state after settings")

print("\nStarting ball tracking test...")
print("Press q to quit.")
print()

frame_times = deque()
read_times = deque(maxlen=120)
process_times = deque(maxlen=120)

total_frames = 0
failed_reads = 0
detections = 0

start = time.monotonic()
last_print = start

while True:
    now = time.monotonic()

    if DURATION > 0 and now - start >= DURATION:
        break

    read_start = time.monotonic()
    ret, frame = cap.read()
    read_end = time.monotonic()

    read_ms = (read_end - read_start) * 1000.0
    read_times.append(read_ms)

    if not ret or frame is None:
        failed_reads += 1
        print("failed read")
        continue

    total_frames += 1
    frame_times.append(read_end)

    while frame_times and read_end - frame_times[0] > 1.0:
        frame_times.popleft()

    process_start = time.monotonic()
    result, detection, mask = track_ball(frame)
    process_end = time.monotonic()

    process_ms = (process_end - process_start) * 1000.0
    process_times.append(process_ms)

    if result != "none":
        detections += 1

    h, w = frame.shape[:2]
    instant_fps = len(frame_times)
    elapsed = process_end - start
    avg_fps = total_frames / elapsed if elapsed > 0 else 0.0
    avg_read_ms = sum(read_times) / len(read_times)
    avg_process_ms = sum(process_times) / len(process_times)

    if detection is not None:
        shape_debug = (
            f"circ={detection['circularity']:.2f} "
            f"fill={detection['fill_ratio']:.2f} "
            f"aspect={detection['aspect']:.2f}"
        )
    else:
        shape_debug = "circ=-- fill=-- aspect=--"

    if process_end - last_print >= 1.0:
        print(
            f"fps={instant_fps:5.1f} | "
            f"avg_fps={avg_fps:5.1f} | "
            f"frame={w}x{h} | "
            f"read_ms={read_ms:6.2f} | "
            f"proc_ms={process_ms:6.2f} | "
            f"avg_read={avg_read_ms:6.2f} | "
            f"avg_proc={avg_process_ms:6.2f} | "
            f"ball={result} | "
            f"{shape_debug} | "
            f"failed={failed_reads}"
        )
        last_print = process_end

    if not NO_DISPLAY:
        display = frame.copy()

        if detection is not None:
            cx = detection["cx"]
            cy = detection["cy"]
            x = detection["x"]
            y = detection["y"]
            bw = detection["w"]
            bh = detection["h"]
            radius = int(detection["radius"])

            cv2.circle(display, (cx, cy), radius, (0, 255, 0), 2)
            cv2.rectangle(display, (x, y), (x + bw, y + bh), (255, 0, 0), 2)
            cv2.circle(display, (cx, cy), 4, (0, 0, 255), -1)

        text1 = f"FPS {instant_fps:.1f} | avg {avg_fps:.1f}"
        text2 = f"read {read_ms:.1f} ms | proc {process_ms:.1f} ms"
        text3 = f"ball: {result}"

        if detection is not None:
            text4 = (
                f"circ {detection['circularity']:.2f} | "
                f"fill {detection['fill_ratio']:.2f} | "
                f"aspect {detection['aspect']:.2f}"
            )
        else:
            text4 = "circ -- | fill -- | aspect --"

        cv2.putText(display, text1, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, text2, (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, text3, (15, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, text4, (15, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Ball Track Debug", display)
        cv2.imshow("Mask", mask)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

elapsed = time.monotonic() - start
measured_fps = total_frames / elapsed if elapsed > 0 else 0.0

print("\nFinal result:")
print(f"requested camera: {WIDTH}x{HEIGHT} @ {FPS}, MJPG={USE_MJPG}")
print(f"final width:      {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
print(f"final height:     {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print(f"final fps:        {cap.get(cv2.CAP_PROP_FPS)}")
print(f"final fourcc:     {repr(fourcc_to_str(cap.get(cv2.CAP_PROP_FOURCC)))}")
print(f"measured fps:     {measured_fps:.2f}")
print(f"total frames:     {total_frames}")
print(f"failed reads:     {failed_reads}")
print(f"detections:       {detections}")

cap.release()
cv2.destroyAllWindows()