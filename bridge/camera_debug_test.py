#!/usr/bin/env python3

import cv2
import time
import argparse
from collections import deque


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=30)
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--no-display", action="store_true")
    args = parser.parse_args()

    print(f"Opening camera {args.device} using AVFoundation...")
    cap = cv2.VideoCapture(args.device, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera {args.device}")

    print("\nInitial camera state:")
    print(f"  width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  fps:    {cap.get(cv2.CAP_PROP_FPS)}")

    print("\nRequesting settings:")
    print(f"  width:  {args.width}")
    print(f"  height: {args.height}")
    print(f"  fps:    {args.fps}")

    ok_w = cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    ok_h = cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    ok_f = cap.set(cv2.CAP_PROP_FPS, args.fps)

    print("\nset() return values:")
    print(f"  width set ok:  {ok_w}")
    print(f"  height set ok: {ok_h}")
    print(f"  fps set ok:    {ok_f}")

    print("\nActual camera state after request:")
    print(f"  width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  fps:    {cap.get(cv2.CAP_PROP_FPS)}")

    print("\nStarting capture test. Press q to quit.\n")

    frame_times = deque()
    total_frames = 0
    failed_reads = 0
    start = time.monotonic()
    last_print = start

    while True:
        now = time.monotonic()
        if now - start >= args.duration:
            break

        read_start = time.monotonic()
        ret, frame = cap.read()
        read_end = time.monotonic()

        if not ret or frame is None:
            failed_reads += 1
            print("Failed to read frame")
            continue

        total_frames += 1
        frame_times.append(read_end)

        while frame_times and read_end - frame_times[0] > 1.0:
            frame_times.popleft()

        h, w = frame.shape[:2]
        read_ms = (read_end - read_start) * 1000.0
        instant_fps = len(frame_times)
        elapsed = read_end - start
        avg_fps = total_frames / elapsed if elapsed > 0 else 0.0

        if read_end - last_print >= 1.0:
            print(
                f"instant_fps={instant_fps:5.1f} | "
                f"avg_fps={avg_fps:5.1f} | "
                f"frame={w}x{h} | "
                f"read_ms={read_ms:6.2f} | "
                f"failed_reads={failed_reads}"
            )
            last_print = read_end

        if not args.no_display:
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
            cv2.imshow("Mac Camera Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    elapsed = time.monotonic() - start
    measured_fps = total_frames / elapsed if elapsed > 0 else 0.0

    print("\nFinal result:")
    print(f"  requested:    {args.width}x{args.height} @ {args.fps}")
    print(f"  final width:  {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"  final height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"  final fps:    {cap.get(cv2.CAP_PROP_FPS)}")
    print(f"  measured fps: {measured_fps:.2f}")
    print(f"  failed reads: {failed_reads}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()