#!/usr/bin/env python3

import cv2
import time
from collections import deque

# Edit only these constants if needed
DEVICE = 0
WIDTH = 640
HEIGHT = 480
FPS = 30
DURATION = 10
USE_MJPG = True
NO_DISPLAY = True


def fourcc_to_str(value):
    value = int(value)
    return "".join(chr((value >> 8 * i) & 0xFF) for i in range(4))


def print_state(cap, label):
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


print(f"Opening camera {DEVICE}...")

cap = cv2.VideoCapture(DEVICE)

if not cap.isOpened():
    raise RuntimeError("Could not open camera")

print_state(cap, "Initial camera state")

print("\nApplying requested settings...")

if USE_MJPG:
    set_prop(cap, cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"), "FOURCC")

set_prop(cap, cv2.CAP_PROP_FRAME_WIDTH, WIDTH, "WIDTH")
set_prop(cap, cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT, "HEIGHT")
set_prop(cap, cv2.CAP_PROP_FPS, FPS, "FPS")
set_prop(cap, cv2.CAP_PROP_BUFFERSIZE, 1, "BUFFER")

print_state(cap, "Actual camera state after settings")

print("\nStarting capture test...\n")

frame_times = deque()
read_times = deque(maxlen=120)

total_frames = 0
failed_reads = 0

start = time.monotonic()
last_print = start

while time.monotonic() - start < DURATION:
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

    h, w = frame.shape[:2]
    instant_fps = len(frame_times)
    elapsed = read_end - start
    avg_fps = total_frames / elapsed if elapsed > 0 else 0.0
    avg_read_ms = sum(read_times) / len(read_times)

    if read_end - last_print >= 1.0:
        print(
            f"instant_fps={instant_fps:5.1f} | "
            f"avg_fps={avg_fps:5.1f} | "
            f"frame={w}x{h} | "
            f"read_ms={read_ms:6.2f} | "
            f"avg_read_ms={avg_read_ms:6.2f} | "
            f"failed_reads={failed_reads}"
        )
        last_print = read_end

    if not NO_DISPLAY:
        text = f"{w}x{h} | FPS {instant_fps:.1f} | read {read_ms:.1f} ms"
        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.imshow("Camera Debug Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

elapsed = time.monotonic() - start
measured_fps = total_frames / elapsed if elapsed > 0 else 0.0

print("\nFinal result:")
print(f"requested:    {WIDTH}x{HEIGHT} @ {FPS}, MJPG={USE_MJPG}")
print(f"final width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
print(f"final height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print(f"final fps:    {cap.get(cv2.CAP_PROP_FPS)}")
print(f"final fourcc: {repr(fourcc_to_str(cap.get(cv2.CAP_PROP_FOURCC)))}")
print(f"measured fps: {measured_fps:.2f}")
print(f"failed reads: {failed_reads}")

cap.release()
cv2.destroyAllWindows()