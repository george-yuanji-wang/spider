"""
bridge_node — pure ROS2 node, no HTTP server.

Reads ctrl  from /tmp/spider_ctrl.json   (written by HTTP server)
Writes tel  to   /tmp/spider_state.json  (read by HTTP server)

Run alongside HTTP server as two separate processes:
    Terminal 1: ros2 run spider_core bridge_node
    Terminal 2: python -m uvicorn bridge.main:app --host 0.0.0.0 --port 8000
"""

import json
import subprocess
import importlib.util
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32

_spec = importlib.util.spec_from_file_location(
    "shared",
    "/home/spider/spider/bridge/shared.py"
)
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)

WATCHED_NODES = {
    "camera":     "camera_status",
    "ball_track": "tracker_status",
    "path_plan":  "planner_status",
    "motor_node": "motor_status",
}


class BridgeNode(Node):

    def __init__(self):
        super().__init__("bridge_node")
        shared.init()

        # ── Subscribers ──────────────────────────────────────────
        self.create_subscription(String,  "ball",       self._on_ball,       10)
        self.create_subscription(String,  "path",       self._on_path,       10)
        self.create_subscription(Float32, "camera/fps", self._on_camera_fps, 10)
        self.create_subscription(Float32, "ball/fps",   self._on_ball_fps,   10)
        self.create_subscription(Float32, "path/fps",   self._on_path_fps,   10)

        # ── Publishers ───────────────────────────────────────────
        self.ctrl_pub = self.create_publisher(String, "spider/ctrl", 10)

        # ── Timers ───────────────────────────────────────────────
        self.create_timer(0.05, self._publish_ctrl)    # 20Hz
        self.create_timer(1.0,  self._check_liveness)  # 1Hz
        self.create_timer(0.5,  self._push_params)     # 2Hz

        state = shared.read_state()
        state["tel"]["connected"] = True
        shared.write_state(state)

        shared.add_cli("Bridge node ready")
        self.get_logger().info("Bridge node ready")

    # ── Subscribers ──────────────────────────────────────────────

    def _on_ball(self, msg: String):
        raw   = msg.data.strip()
        state = shared.read_state()
        if raw in ("none", ""):
            state["tel"]["ball"] = None
        else:
            try:
                cx, cy, x, y, w, h    = [float(v) for v in raw.split(",")]
                state["tel"]["ball"]  = {
                    "cx": cx, "cy": cy,
                    "x":  x,  "y":  y,
                    "w":  w,  "h":  h,
                }
            except ValueError:
                self.get_logger().warn(f"Malformed ball: {raw}")
                state["tel"]["ball"] = None
        shared.write_state(state)

    def _on_path(self, msg: String):
        state = shared.read_state()
        try:
            state["tel"]["path"] = json.loads(msg.data.strip())
        except json.JSONDecodeError:
            state["tel"]["path"] = []
        shared.write_state(state)

    def _on_camera_fps(self, msg: Float32):
        state = shared.read_state()
        state["tel"]["camera_fps"] = round(msg.data, 1)
        shared.write_state(state)

    def _on_ball_fps(self, msg: Float32):
        state = shared.read_state()
        state["tel"]["tracker_fps"] = round(msg.data, 1)
        shared.write_state(state)

    def _on_path_fps(self, msg: Float32):
        state = shared.read_state()
        state["tel"]["planner_fps"] = round(msg.data, 1)
        shared.write_state(state)

    # ── Ctrl publisher ───────────────────────────────────────────

    def _publish_ctrl(self):
        ctrl     = shared.read_ctrl()
        msg      = String()
        msg.data = json.dumps(ctrl)
        self.ctrl_pub.publish(msg)

    # ── Node liveness ────────────────────────────────────────────

    def _check_liveness(self):
        try:
            live = self.get_node_names()
        except Exception:
            return

        state = shared.read_state()
        for node_name, status_key in WATCHED_NODES.items():
            was = state["tel"][status_key]
            now = node_name in live
            if was != now:
                state["tel"][status_key] = now
                label  = node_name.replace("_", " ").title()
                status = "healthy" if now else "malfunctioning"
                shared.add_cli(f"{label}: {status}")
                self.get_logger().info(f"{node_name}: {status}")
        shared.write_state(state)

    # ── Param push ───────────────────────────────────────────────

    def _push_params(self):
        params = shared.read_params()
        ball   = params.get("ball", {})
        if not ball.get("dirty", False):
            return

        ball["dirty"] = False
        shared.write_params({"ball": ball})

        push   = {k: v for k, v in ball.items() if k != "dirty"}
        failed = False
        for name, value in push.items():
            try:
                subprocess.Popen(
                    ["ros2", "param", "set", "/ball_track", name, str(value)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warn(f"Param push failed {name}: {e}")
                shared.add_cli(f"Param push failed: {name}")
                failed = True
                break

        if not failed:
            self.get_logger().info("Ball track params pushed")
            shared.add_cli("Ball track params applied")

    # ── Shutdown ─────────────────────────────────────────────────

    def destroy_node(self):
        state = shared.read_state()
        state["tel"]["connected"] = False
        shared.write_state(state)
        shared.add_cli("Bridge node shutting down")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()