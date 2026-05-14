"""
auto_node

State machine for autonomous ball capture and mat deposit task.

States:
    IDLE            — waiting, do nothing
    SEARCH_BALL     — rotate slowly, looking for blue ball
    APPROACH_BALL   — drive toward ball with steering correction
    CAPTURE         — stop, open claw, drive forward, close claw
    SEARCH_MAT      — rotate slowly, looking for red mat
    APPROACH_MAT    — drive toward mat with steering correction
    DEPOSIT         — stop, open claw, pause, back up
    DONE            — task complete, return to IDLE

Subscribes:
    vision/target       std_msgs/String     target detection
    spider/ctrl         std_msgs/String     to read mode/armed
    auto/set_state      std_msgs/String     override state from GUI

Publishes:
    path/cmd            std_msgs/String     motor command JSON
    auto/state          std_msgs/String     current state name for GUI

Parameters:
    approach_speed      int     forward speed during approach   default 80
    steer_gain          float   steering correction multiplier  default 0.3
    dead_zone           int     pixel error margin              default 40
    ball_capture_cy     int     y-position for ball capture zone
    capture_x_margin    int     horizontal centering margin for capture
    align_turn_speed    int     in-place turn speed for alignment
    mat_deposit_cy      int     y-position for mat deposit zone
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import String
import subprocess
import json
import time


# ── Timing constants ─────────────────────────────────────────────
SEARCH_TURN_SPEED   = 60
CAPTURE_OPEN_SEC    = 1.0
CAPTURE_DRIVE_SEC   = 2.0
CAPTURE_CLOSE_SEC   = 1.0
DEPOSIT_OPEN_SEC    = 2.0
DEPOSIT_BACK_SEC    = 2.0
APPROACH_LOST_SEC   = 0.5

# ── Capture alignment thresholds ─────────────────────────────────
BALL_CAPTURE_CY     = 420
CAPTURE_X_MARGIN    = 45
ALIGN_TURN_SPEED    = 50

# ── Mat deposit thresholds ───────────────────────────────────────
MAT_DEPOSIT_CY      = 420   # same logic as ball — cy below this → deposit zone
MAT_X_MARGIN        = 60    # slightly looser margin for mat

FRAME_CX            = 320

# ── Valid states for override ────────────────────────────────────
VALID_STATES = {
    "IDLE", "SEARCH_BALL", "APPROACH_BALL", "CAPTURE",
    "SEARCH_MAT", "APPROACH_MAT", "DEPOSIT", "DONE",
}


class AutoNode(Node):

    def __init__(self):
        super().__init__("auto_node")

        # ── Parameters ───────────────────────────────────────────
        self.declare_parameter("approach_speed",   80)
        self.declare_parameter("steer_gain",       0.3)
        self.declare_parameter("dead_zone",        40)
        self.declare_parameter("ball_capture_cy",  BALL_CAPTURE_CY)
        self.declare_parameter("capture_x_margin", CAPTURE_X_MARGIN)
        self.declare_parameter("align_turn_speed", ALIGN_TURN_SPEED)
        self.declare_parameter("mat_deposit_cy",   MAT_DEPOSIT_CY)
        self._load_params()

        # ── State ────────────────────────────────────────────────
        self._state       = "IDLE"
        self._armed       = False
        self._mode        = "manual"
        self._target      = None
        self._last_seen   = 0.0
        self._phase_start = 0.0
        self._claw        = False

        # ── Subscribers ──────────────────────────────────────────
        self.create_subscription(String, "vision/target",  self._on_target,    10)
        self.create_subscription(String, "spider/ctrl",    self._on_ctrl,      10)
        self.create_subscription(String, "auto/set_state", self._on_set_state, 10)

        # ── Publishers ───────────────────────────────────────────
        self.cmd_pub   = self.create_publisher(String, "path/cmd",   10)
        self.state_pub = self.create_publisher(String, "auto/state", 10)

        # ── Timer ────────────────────────────────────────────────
        self.create_timer(0.05, self._tick)

        self.add_on_set_parameters_callback(self._on_param_change)
        self.get_logger().info("Auto node ready")

    def _load_params(self):
        self.approach_speed   = self.get_parameter("approach_speed").value
        self.steer_gain       = self.get_parameter("steer_gain").value
        self.dead_zone        = self.get_parameter("dead_zone").value
        self.ball_capture_cy  = self.get_parameter("ball_capture_cy").value
        self.capture_x_margin = self.get_parameter("capture_x_margin").value
        self.align_turn_speed = self.get_parameter("align_turn_speed").value
        self.mat_deposit_cy   = self.get_parameter("mat_deposit_cy").value

    # ── Subscribers ──────────────────────────────────────────────

    def _on_target(self, msg: String):
        raw = msg.data.strip()
        if raw in ("none", ""):
            self._target = None
        else:
            try:
                cx, cy, x, y, w, h = [float(v) for v in raw.split(",")]
                self._target = {"cx": cx, "cy": cy, "x": x, "y": y, "w": w, "h": h}
                self._last_seen = time.monotonic()
            except ValueError:
                self._target = None

    def _on_ctrl(self, msg: String):
        try:
            d = json.loads(msg.data)
            self._armed = bool(d.get("armed", False))
            self._mode  = str(d.get("mode", "manual"))
        except (json.JSONDecodeError, ValueError):
            pass

    def _on_set_state(self, msg: String):
        """
        GUI debug override — jump directly to any state.
        Only honoured when armed and in auto mode.
        """
        requested = msg.data.strip().upper()
        if requested not in VALID_STATES:
            self.get_logger().warn(f"Invalid state override: {requested}")
            return
        if not self._armed or self._mode != "auto":
            self.get_logger().warn("State override ignored — not armed/auto")
            return
        self.get_logger().info(f"State override: {self._state} → {requested}")
        self._transition(requested)

    # ── Vision switch ────────────────────────────────────────────

    def _set_detect_mode(self, mode: str):
        subprocess.Popen(
            ["ros2", "param", "set", "/vision_node", "detect_mode", mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.get_logger().info(f"Vision mode → {mode}")

    # ── Commands ─────────────────────────────────────────────────

    def _send_cmd(self, left: int, right: int, claw: bool):
        msg      = String()
        msg.data = json.dumps({"left": left, "right": right, "claw": 1 if claw else 0})
        self.cmd_pub.publish(msg)

    def _stop(self, claw: bool = False):
        self._send_cmd(0, 0, claw)

    # ── Steering ─────────────────────────────────────────────────

    def _steer(self, target: dict | None, claw: bool):
        spd = self.approach_speed

        if target is None:
            if time.monotonic() - self._last_seen < APPROACH_LOST_SEC:
                self._send_cmd(spd, spd, claw)
            else:
                self._stop(claw)
            return

        error      = target["cx"] - FRAME_CX
        correction = min(abs(error) * self.steer_gain, spd * 0.8)

        if error > self.dead_zone:
            left, right = int(spd), int(spd - correction)
        elif error < -self.dead_zone:
            left, right = int(spd - correction), int(spd)
        else:
            left, right = int(spd), int(spd)

        self._send_cmd(left, right, claw)

    def _align_in_place(self, target: dict, claw: bool, x_margin: int):
        """Rotate in place to center target horizontally."""
        error = target["cx"] - FRAME_CX
        turn  = int(self.align_turn_speed)

        if error > x_margin:
            self._send_cmd(turn, -turn, claw)
        elif error < -x_margin:
            self._send_cmd(-turn, turn, claw)
        else:
            self._stop(claw)

    # ── State machine ────────────────────────────────────────────

    def _transition(self, new_state: str):
        self.get_logger().info(f"State: {self._state} → {new_state}")
        self._state       = new_state
        self._phase_start = time.monotonic()

        if new_state in ("SEARCH_BALL", "APPROACH_BALL", "CAPTURE"):
            self._set_detect_mode("ball")
        elif new_state in ("SEARCH_MAT", "APPROACH_MAT", "DEPOSIT"):
            self._set_detect_mode("mat")

        msg      = String()
        msg.data = new_state
        self.state_pub.publish(msg)

    def _elapsed(self) -> float:
        return time.monotonic() - self._phase_start

    def _tick(self):
        if not self._armed or self._mode != "auto":
            self._stop(self._claw)
            msg      = String()
            msg.data = self._state
            self.state_pub.publish(msg)
            return

        t = self._target

        # ── IDLE ─────────────────────────────────────────────────
        if self._state == "IDLE":
            self._claw = False
            self._stop(self._claw)
            self._transition("SEARCH_BALL")

        # ── SEARCH_BALL ──────────────────────────────────────────
        elif self._state == "SEARCH_BALL":
            if t is not None:
                self._transition("APPROACH_BALL")
            else:
                self._send_cmd(SEARCH_TURN_SPEED, -SEARCH_TURN_SPEED, self._claw)

        # ── APPROACH_BALL ────────────────────────────────────────
        elif self._state == "APPROACH_BALL":
            if t is None and time.monotonic() - self._last_seen > APPROACH_LOST_SEC:
                self._transition("SEARCH_BALL")
            elif t is None:
                self._steer(t, self._claw)
            else:
                x_error = t["cx"] - FRAME_CX
                if t["cy"] >= self.ball_capture_cy:
                    if abs(x_error) <= self.capture_x_margin:
                        self._transition("CAPTURE")
                    else:
                        self._align_in_place(t, self._claw, self.capture_x_margin)
                else:
                    self._steer(t, self._claw)

        # ── CAPTURE ──────────────────────────────────────────────
        elif self._state == "CAPTURE":
            elapsed = self._elapsed()
            if elapsed < CAPTURE_OPEN_SEC:
                self._claw = False
                self._stop(self._claw)
            elif elapsed < CAPTURE_OPEN_SEC + CAPTURE_DRIVE_SEC:
                self._claw = False
                self._send_cmd(self.approach_speed, self.approach_speed, self._claw)
            elif elapsed < CAPTURE_OPEN_SEC + CAPTURE_DRIVE_SEC + CAPTURE_CLOSE_SEC:
                self._claw = True
                self._stop(self._claw)
            else:
                self._transition("SEARCH_MAT")

        # ── SEARCH_MAT ───────────────────────────────────────────
        elif self._state == "SEARCH_MAT":
            if t is not None:
                self._transition("APPROACH_MAT")
            else:
                self._send_cmd(SEARCH_TURN_SPEED, -SEARCH_TURN_SPEED, self._claw)

        # ── APPROACH_MAT ─────────────────────────────────────────
        elif self._state == "APPROACH_MAT":
            if t is None and time.monotonic() - self._last_seen > APPROACH_LOST_SEC:
                self._transition("SEARCH_MAT")
            elif t is None:
                self._steer(t, self._claw)
            else:
                x_error = t["cx"] - FRAME_CX
                if t["cy"] >= self.mat_deposit_cy:
                    if abs(x_error) <= MAT_X_MARGIN:
                        self._transition("DEPOSIT")
                    else:
                        self._align_in_place(t, self._claw, MAT_X_MARGIN)
                else:
                    self._steer(t, self._claw)

        # ── DEPOSIT ──────────────────────────────────────────────
        elif self._state == "DEPOSIT":
            elapsed = self._elapsed()
            if elapsed < DEPOSIT_OPEN_SEC:
                self._claw = False
                self._stop(self._claw)
            elif elapsed < DEPOSIT_OPEN_SEC + DEPOSIT_BACK_SEC:
                spd = self.approach_speed
                self._send_cmd(-spd, -spd, self._claw)
            else:
                self._transition("DONE")

        # ── DONE ─────────────────────────────────────────────────
        elif self._state == "DONE":
            self._claw = False
            self._stop(self._claw)
            self.get_logger().info("Task complete")
            self._transition("IDLE")

    def _on_param_change(self, params: list[Parameter]):
        for p in params:
            if hasattr(self, p.name):
                setattr(self, p.name, p.value)
                self.get_logger().info(f"Param updated: {p.name} = {p.value}")
        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = AutoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()