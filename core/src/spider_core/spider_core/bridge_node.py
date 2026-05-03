"""
bridge_node

ROS2 node that bridges the GUI (Next.js) with the ROS2 graph.
Runs FastAPI on a background thread; rclpy spins on the main thread.

Run:
    ros2 run spider_core bridge_node

HTTP API (port 8000):
    GET  /api/health   → { ok: true }
    GET  /api/tel      → telemetry object
    POST /api/ctrl     → update ctrl state
    POST /api/params   → update ball tracking params
    GET  /api/cli      → { messages: [...] }

Subscribes:
    ball                std_msgs/String      "cx,cy,x,y,w,h" or "none"
    path                std_msgs/String      JSON [{x,y}, ...]
    camera/fps          std_msgs/Float32
    ball/fps            std_msgs/Float32
    path/fps            std_msgs/Float32

Publishes:
    spider/ctrl         std_msgs/String      JSON ctrl → motor_node

Parameter push:
    Uses ros2 param set subprocess calls to update ball_track node params.
    Triggered when GUI sends POST /api/params.
"""

import threading
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────────────────────────────

_lock = threading.Lock()


@dataclass
class _Tel:
    connected:      bool  = False
    camera_status:  bool  = False
    motor_status:   bool  = False
    tracker_status: bool  = False
    planner_status: bool  = False
    camera_fps:     float = 0.0
    tracker_fps:    float = 0.0
    planner_fps:    float = 0.0
    ball:           Optional[dict] = None
    path:           list  = field(default_factory=list)


@dataclass
class _Ctrl:
    armed:       bool = False
    mode:        str  = "manual"
    input_left:  int  = 0
    input_right: int  = 0
    speed:       int  = 50


@dataclass
class _BallParams:
    hue_low:     int = 90
    hue_high:    int = 115
    sat_low:     int = 80
    sat_high:    int = 255
    val_low:     int = 80
    val_high:    int = 255
    min_radius:  int = 8
    blur_kernel: int = 7
    dilate_iter: int = 1


_tel          = _Tel()
_ctrl         = _Ctrl()
_ball_params  = _BallParams()
_cli: list[dict] = []
_params_dirty = False


def _add_cli(text: str):
    with _lock:
        _cli.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text":      text,
        })


# ─────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CtrlPayload(BaseModel):
    armed:       bool
    mode:        str
    input_left:  int
    input_right: int
    speed:       int


class BallParamsPayload(BaseModel):
    hue_low:     int
    hue_high:    int
    sat_low:     int
    sat_high:    int
    val_low:     int
    val_high:    int
    min_radius:  int
    blur_kernel: int
    dilate_iter: int


class ParamsPayload(BaseModel):
    ball: BallParamsPayload


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tel")
def get_tel():
    with _lock:
        return asdict(_tel)


@app.post("/api/ctrl")
def post_ctrl(payload: CtrlPayload):
    with _lock:
        _ctrl.armed       = payload.armed
        _ctrl.mode        = payload.mode
        _ctrl.input_left  = payload.input_left
        _ctrl.input_right = payload.input_right
        _ctrl.speed       = payload.speed
    return {"ok": True}


@app.post("/api/params")
def post_params(payload: ParamsPayload):
    global _params_dirty
    b = payload.ball
    with _lock:
        _ball_params.hue_low     = b.hue_low
        _ball_params.hue_high    = b.hue_high
        _ball_params.sat_low     = b.sat_low
        _ball_params.sat_high    = b.sat_high
        _ball_params.val_low     = b.val_low
        _ball_params.val_high    = b.val_high
        _ball_params.min_radius  = b.min_radius
        _ball_params.blur_kernel = b.blur_kernel
        _ball_params.dilate_iter = b.dilate_iter
        _params_dirty = True
    _add_cli(
        f"Ball params updated — "
        f"H:{b.hue_low}-{b.hue_high} "
        f"S:{b.sat_low}-{b.sat_high} "
        f"V:{b.val_low}-{b.val_high} "
        f"r:{b.min_radius} k:{b.blur_kernel} d:{b.dilate_iter}"
    )
    return {"ok": True}


@app.get("/api/cli")
def get_cli():
    with _lock:
        return {"messages": list(_cli)}


# ─────────────────────────────────────────────────────────────────
# ROS2 node
# ─────────────────────────────────────────────────────────────────

WATCHED_NODES = {
    "camera":     "camera_status",
    "ball_track": "tracker_status",
    "path_plan":  "planner_status",
    "motor_node": "motor_status",
}

BALL_TRACK_NODE_NAME = "/ball_track"


class BridgeNode(Node):

    def __init__(self):
        super().__init__("bridge_node")

        # ── Subscribers ──────────────────────────────────────────
        self.create_subscription(String,  "ball",       self._on_ball,       10)
        self.create_subscription(String,  "path",       self._on_path,       10)
        self.create_subscription(Float32, "camera/fps", self._on_camera_fps, 10)
        self.create_subscription(Float32, "ball/fps",   self._on_ball_fps,   10)
        self.create_subscription(Float32, "path/fps",   self._on_path_fps,   10)

        # ── Publishers ───────────────────────────────────────────
        self.ctrl_pub = self.create_publisher(String, "spider/ctrl", 10)

        # ── Timers ───────────────────────────────────────────────
        self.create_timer(1.0 / 20.0, self._publish_ctrl)   # 20Hz ctrl
        self.create_timer(1.0,        self._check_liveness)  # 1Hz health
        self.create_timer(0.5,        self._push_params)     # 2Hz param check

        with _lock:
            _tel.connected = True

        _add_cli("Bridge node ready")
        self.get_logger().info("Bridge node ready")

    # ── Subscriber callbacks ─────────────────────────────────────

    def _on_ball(self, msg: String):
        raw = msg.data.strip()
        with _lock:
            if raw in ("none", ""):
                _tel.ball = None
            else:
                try:
                    cx, cy, x, y, w, h = [float(v) for v in raw.split(",")]
                    _tel.ball = {
                        "cx": cx, "cy": cy,
                        "x":  x,  "y":  y,
                        "w":  w,  "h":  h,
                    }
                except ValueError:
                    self.get_logger().warn(f"Malformed ball msg: {raw}")
                    _tel.ball = None

    def _on_path(self, msg: String):
        raw = msg.data.strip()
        with _lock:
            try:
                _tel.path = json.loads(raw)
            except json.JSONDecodeError:
                self.get_logger().warn(f"Malformed path msg: {raw}")
                _tel.path = []

    def _on_camera_fps(self, msg: Float32):
        with _lock:
            _tel.camera_fps = round(msg.data, 1)

    def _on_ball_fps(self, msg: Float32):
        with _lock:
            _tel.tracker_fps = round(msg.data, 1)

    def _on_path_fps(self, msg: Float32):
        with _lock:
            _tel.planner_fps = round(msg.data, 1)

    # ── Ctrl publisher ───────────────────────────────────────────

    def _publish_ctrl(self):
        with _lock:
            c = _ctrl
        msg      = String()
        msg.data = json.dumps({
            "armed":       c.armed,
            "mode":        c.mode,
            "input_left":  c.input_left,
            "input_right": c.input_right,
            "speed":       c.speed,
        })
        self.ctrl_pub.publish(msg)

    # ── Node liveness ────────────────────────────────────────────

    def _check_liveness(self):
        try:
            live = self.get_node_names()
        except Exception:
            return

        with _lock:
            for node_name, status_key in WATCHED_NODES.items():
                was = getattr(_tel, status_key)
                now = node_name in live
                if was != now:
                    setattr(_tel, status_key, now)
                    label  = node_name.replace("_", " ").title()
                    status = "healthy" if now else "malfunctioning"
                    _add_cli(f"{label}: {status}")
                    self.get_logger().info(f"{node_name}: {status}")

    # ── Param push ───────────────────────────────────────────────

    def _push_params(self):
        global _params_dirty
        with _lock:
            if not _params_dirty:
                return
            # Copy values before releasing lock
            p = _BallParams(
                hue_low     = _ball_params.hue_low,
                hue_high    = _ball_params.hue_high,
                sat_low     = _ball_params.sat_low,
                sat_high    = _ball_params.sat_high,
                val_low     = _ball_params.val_low,
                val_high    = _ball_params.val_high,
                min_radius  = _ball_params.min_radius,
                blur_kernel = _ball_params.blur_kernel,
                dilate_iter = _ball_params.dilate_iter,
            )
            _params_dirty = False

        params = {
            "hue_low":     p.hue_low,
            "hue_high":    p.hue_high,
            "sat_low":     p.sat_low,
            "sat_high":    p.sat_high,
            "val_low":     p.val_low,
            "val_high":    p.val_high,
            "min_radius":  p.min_radius,
            "blur_kernel": p.blur_kernel,
            "dilate_iter": p.dilate_iter,
        }

        failed = False
        for name, value in params.items():
            try:
                subprocess.Popen(
                    ["ros2", "param", "set", BALL_TRACK_NODE_NAME, name, str(value)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warn(f"Param push failed for {name}: {e}")
                _add_cli(f"Param push failed: {name} — {e}")
                failed = True
                break

        if not failed:
            self.get_logger().info("Ball track params pushed")
            _add_cli("Ball track params applied")

    # ── Shutdown ─────────────────────────────────────────────────

    def destroy_node(self):
        with _lock:
            _tel.connected = False
        _add_cli("Bridge node shutting down")
        super().destroy_node()


# ─────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────

def main(args=None):
    import threading
    import uvicorn
    import signal

    rclpy.init(args=args)
    node = BridgeNode()

    # Track server handle for clean shutdown
    server_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="warning",
    )
    server = uvicorn.Server(server_config)

    # Spin rclpy in background thread
    spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True,
    )
    spin_thread.start()

    # Handle SIGINT/SIGTERM cleanly
    def shutdown(signum, frame):
        node.get_logger().info("Shutdown signal received")
        server.should_exit = True

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Uvicorn on main thread — blocks until server.should_exit
    try:
        server.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
        node.get_logger().info("Bridge node stopped cleanly")

if __name__ == "__main__":
    main()