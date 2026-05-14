"""
bridge_node — pure ROS2 node, no HTTP server.
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
    "camera":      "camera_status",
    "vision_node": "tracker_status",
    "auto_node":   "planner_status",
    "motor_node":  "motor_status",
    "stream_node": "stream_status",
}


class BridgeNode(Node):

    def __init__(self):
        super().__init__("bridge_node")
        shared.init()

        # ── Subscribers ──────────────────────────────────────────
        self.create_subscription(String,  "vision/target", self._on_vision,     10)
        self.create_subscription(String,  "path",          self._on_path,       10)
        self.create_subscription(String,  "auto/state",    self._on_auto_state, 10)
        self.create_subscription(Float32, "camera/fps",    self._on_camera_fps, 10)
        self.create_subscription(Float32, "vision/fps",    self._on_vision_fps, 10)
        self.create_subscription(Float32, "path/fps",      self._on_path_fps,   10)

        # ── Publishers ───────────────────────────────────────────
        self.ctrl_pub      = self.create_publisher(String, "spider/ctrl",    10)
        self.set_state_pub = self.create_publisher(String, "auto/set_state", 10)

        # ── Timers ───────────────────────────────────────────────
        self.create_timer(0.05, self._publish_ctrl)
        self.create_timer(1.0,  self._check_liveness)
        self.create_timer(0.5,  self._push_params)
        self.create_timer(0.1,  self._poll_auto_cmd)   # 10Hz auto cmd check

        state = shared.read_state()
        state["tel"]["connected"] = True
        shared.write_state(state)

        shared.add_cli("Bridge node ready")
        self.get_logger().info("Bridge node ready")

    # ── Subscribers ──────────────────────────────────────────────

    def _on_vision(self, msg: String):
        raw   = msg.data.strip()
        state = shared.read_state()
        if raw in ("none", ""):
            state["tel"]["ball"] = None
        else:
            try:
                cx, cy, x, y, w, h = [float(v) for v in raw.split(",")]
                state["tel"]["ball"] = {
                    "cx": cx, "cy": cy,
                    "x":  x,  "y":  y,
                    "w":  w,  "h":  h,
                }
            except ValueError:
                self.get_logger().warn(f"Malformed vision/target: {raw}")
                state["tel"]["ball"] = None
        shared.write_state(state)

    def _on_path(self, msg: String):
        state = shared.read_state()
        try:
            state["tel"]["path"] = json.loads(msg.data.strip())
        except json.JSONDecodeError:
            state["tel"]["path"] = []
        shared.write_state(state)

    def _on_auto_state(self, msg: String):
        state = shared.read_state()
        state["tel"]["auto_state"] = msg.data.strip()
        shared.write_state(state)

    def _on_camera_fps(self, msg: Float32):
        state = shared.read_state()
        state["tel"]["camera_fps"] = round(msg.data, 1)
        shared.write_state(state)

    def _on_vision_fps(self, msg: Float32):
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

    # ── Auto state override ──────────────────────────────────────

    def _poll_auto_cmd(self):
        cmd = shared.read_auto_cmd()
        state = cmd.get("state", "")
        if not state:
            return
        msg      = String()
        msg.data = state
        self.set_state_pub.publish(msg)
        shared.clear_auto_cmd()
        self.get_logger().info(f"Auto state override published: {state}")

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

        ball = params.get("ball", {})
        if ball.get("dirty", False):
            ball["dirty"] = False
            shared.write_params({**params, "ball": ball})
            push = {k: v for k, v in ball.items() if k != "dirty"}
            failed = False
            for name, value in push.items():
                try:
                    subprocess.Popen(
                        ["ros2", "param", "set", "/vision_node", name, str(value)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception as e:
                    self.get_logger().warn(f"Vision param push failed {name}: {e}")
                    shared.add_cli(f"Vision param push failed: {name}")
                    failed = True
                    break
            if not failed:
                self.get_logger().info("Vision params pushed")
                shared.add_cli("Vision params applied")

        path = params.get("path", {})
        if path.get("dirty", False):
            path["dirty"] = False
            shared.write_params({**params, "path": path})
            push = {k: v for k, v in path.items() if k != "dirty"}
            failed = False
            for name, value in push.items():
                try:
                    subprocess.Popen(
                        ["ros2", "param", "set", "/auto_node", name, str(value)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception as e:
                    self.get_logger().warn(f"Auto param push failed {name}: {e}")
                    shared.add_cli(f"Auto param push failed: {name}")
                    failed = True
                    break
            if not failed:
                self.get_logger().info("Auto params pushed")
                shared.add_cli("Auto params applied")

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