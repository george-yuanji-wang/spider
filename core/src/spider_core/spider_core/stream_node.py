"""
stream_node

Subscribes to /camera/image_raw and serves an MJPEG stream over HTTP.
Access at: http://<pi-ip>:8001/stream

This is a standalone HTTP server — no ROS HTTP conflicts because
it runs on port 8001, separate from bridge HTTP on port 8000.

Subscribes:
    /camera/image_raw   sensor_msgs/Image
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np
from cv_bridge import CvBridge

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

STREAM_PORT    = 8001
JPEG_QUALITY   = 80      # 0-100, lower = faster, higher = better quality
TARGET_FPS     = 15      # cap stream FPS to avoid overwhelming network
FRAME_INTERVAL = 1.0 / TARGET_FPS

# ── Shared latest frame ───────────────────────────────────────────
_frame_lock   = threading.Lock()
_latest_frame: bytes | None = None   # JPEG bytes
_last_encode  = 0.0


def _set_frame(bgr_frame: np.ndarray):
    global _latest_frame, _last_encode

    now = time.monotonic()
    if now - _last_encode < FRAME_INTERVAL:
        return   # drop frame, too soon

    _, buf = cv2.imencode(
        ".jpg", bgr_frame,
        [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    )
    with _frame_lock:
        _latest_frame = buf.tobytes()
        _last_encode  = now


def _get_frame() -> bytes | None:
    with _frame_lock:
        return _latest_frame


# ── MJPEG HTTP handler ────────────────────────────────────────────

BOUNDARY = b"--frame"

class MJPEGHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass   # suppress access logs

    def do_GET(self):
        if self.path == "/stream":
            self._serve_stream()
        elif self.path == "/snapshot":
            self._serve_snapshot()
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header(
            "Content-Type",
            f"multipart/x-mixed-replace; boundary=frame"
        )
        self.end_headers()

        try:
            while True:
                frame = _get_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                self.wfile.write(
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame +
                    b"\r\n"
                )
                self.wfile.flush()
                time.sleep(FRAME_INTERVAL)
        except (BrokenPipeError, ConnectionResetError):
            pass   # client disconnected — normal

    def _serve_snapshot(self):
        frame = _get_frame()
        if frame is None:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.end_headers()
        self.wfile.write(frame)


# ── ROS node ──────────────────────────────────────────────────────

class StreamNode(Node):

    def __init__(self):
        super().__init__("stream_node")

        self.declare_parameter("jpeg_quality", JPEG_QUALITY)
        self.declare_parameter("target_fps",   TARGET_FPS)
        self.declare_parameter("port",         STREAM_PORT)

        self._bridge = CvBridge()

        self.create_subscription(
            Image,
            "camera/image_raw",
            self._on_image,
            10,
        )

        port = self.get_parameter("port").value
        threading.Thread(
            target=self._start_server,
            args=(port,),
            daemon=True,
        ).start()

        self.get_logger().info(
            f"Stream node ready — http://<pi-ip>:{port}/stream"
        )

    def _on_image(self, msg: Image):
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            _set_frame(frame)
        except Exception as e:
            self.get_logger().warn(f"Frame decode error: {e}")

    def _start_server(self, port: int):
        server = HTTPServer(("0.0.0.0", port), MJPEGHandler)
        server.serve_forever()


def main(args=None):
    rclpy.init(args=args)
    node = StreamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()