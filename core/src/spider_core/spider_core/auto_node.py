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

Publishes:
    path/cmd            std_msgs/String     "left,right,claw" motor command
    auto/state          std_msgs/String     current state name for GUI

Parameters (tunable from GUI):
    approach_speed      int     forward speed during approach   default 40
    steer_gain          float   steering correction multiplier  default 0.3
    dead_zone           int     pixel error margin              default 40
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
import subprocess
import json
import time


# ── Tunable timing constants — adjust after testing ──────────────
SEARCH_TURN_SPEED   = 60    # rotation speed when searching
CAPTURE_OPEN_SEC    = 0.5   # time to wait after opening claw
CAPTURE_DRIVE_SEC   = 1.5   # time to drive forward after opening claw
CAPTURE_CLOSE_SEC   = 0.8   # time to wait after closing claw
DEPOSIT_OPEN_SEC    = 0.8   # time claw stays open at deposit
DEPOSIT_BACK_SEC    = 1.0   # time to reverse after deposit
APPROACH_LOST_SEC   = 0.5   # drive straight if target lost for this long

# ── Target size thresholds ───────────────────────────────────────
BALL_CAPTURE_WIDTH  = 380   # px — ball this wide → start capture
MAT_DEPOSIT_WIDTH   = 400   # px — mat this wide → start deposit

FRAME_CX            = 320   # frame horizontal centre


class AutoNode(Node):

    def __init__(self):
        super().__init__("auto_node")

        # ── Parameters ───────────────────────────────────────────
        self.declare_parameter("approach_speed", 80)
        self.declare_parameter("steer_gain",     0.3)
        self.declare_parameter("dead_zone",      40)
        self._load_params()

        # ── State machine ────────────────────────────────────────
        # Persists across manual/auto switches
        self._state       = "IDLE"
        self._armed       = False
        self._mode        = "manual"
        self._target      = None   # latest parsed vision target
        self._last_seen   = 0.0   # time of last valid detection
        self._phase_start = 0.0   # time current timed phase started

        # Claw state owned here in auto mode
        self._claw        = False  # False=open, True=closed

        # ── Subscribers ──────────────────────────────────────────
        self.create_subscription(
            String, "vision/target", self._on_target, 10
        )
        self.create_subscription(
            String, "spider/ctrl", self._on_ctrl, 10
        )

        # ── Publishers ───────────────────────────────────────────
        self.cmd_pub   = self.create_publisher(String, "path/cmd",   10)
        self.state_pub = self.create_publisher(String, "auto/state", 10)

        # ── Timer — runs state machine at 20Hz ───────────────────
        self.create_timer(0.05, self._tick)

        self.add_on_set_parameters_callback(self._on_param_change)

        self.get_logger().info("Auto node ready")

    def _load_params(self):
        self.approach_speed = self.get_parameter("approach_speed").value
        self.steer_gain     = self.get_parameter("steer_gain").value
        self.dead_zone      = self.get_parameter("dead_zone").value

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

    # ── Vision mode switch ───────────────────────────────────────

    def _set_detect_mode(self, mode: str):
        """Switch vision_node between ball and mat detection."""
        subprocess.Popen(
            ["ros2", "param", "set", "/vision_node", "detect_mode", mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.get_logger().info(f"Vision mode → {mode}")

    # ── Command publishing ───────────────────────────────────────

    def _send_cmd(self, left: int, right: int, claw: bool):
        """Publish motor command to path/cmd topic."""
        msg      = String()
        msg.data = json.dumps({
            "left":  left,
            "right": right,
            "claw":  1 if claw else 0,
        })
        self.cmd_pub.publish(msg)

    def _stop(self, claw: bool = False):
        self._send_cmd(0, 0, claw)

    # ── Steering ─────────────────────────────────────────────────

    def _steer(self, target: dict | None, claw: bool):
        """
        Drive toward target with continuous steering correction.
        If target is lost for < APPROACH_LOST_SEC, drive straight.
        """
        spd = self.approach_speed

        if target is None:
            # Lost target briefly — drive straight
            if time.monotonic() - self._last_seen < APPROACH_LOST_SEC:
                self._send_cmd(spd, spd, claw)
            else:
                self._stop(claw)
            return

        error      = target["cx"] - FRAME_CX
        correction = min(abs(error) * self.steer_gain, spd * 0.8)

        if error > self.dead_zone:
            # Target is to the right — turn right (slow left)
            left  = int(spd)
            right = int(spd - correction)
        elif error < -self.dead_zone:
            # Target is to the left — turn left (slow right)
            left  = int(spd - correction)
            right = int(spd)
        else:
            # Centered — drive straight
            left  = spd
            right = spd

        self._send_cmd(left, right, claw)

    # ── State machine ────────────────────────────────────────────

    def _transition(self, new_state: str):
        self.get_logger().info(f"State: {self._state} → {new_state}")
        self._state       = new_state
        self._phase_start = time.monotonic()

        # Switch vision mode when entering relevant states
        if new_state in ("SEARCH_BALL", "APPROACH_BALL", "CAPTURE"):
            self._set_detect_mode("ball")
        elif new_state in ("SEARCH_MAT", "APPROACH_MAT", "DEPOSIT"):
            self._set_detect_mode("mat")

        # Publish state for GUI
        msg      = String()
        msg.data = new_state
        self.state_pub.publish(msg)

    def _elapsed(self) -> float:
        return time.monotonic() - self._phase_start

    def _tick(self):
        # Only run state machine when armed and in auto mode
        if not self._armed or self._mode != "auto":
            self._stop(self._claw)
            # Publish state so GUI stays updated
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
                # Rotate slowly to search
                self._send_cmd(SEARCH_TURN_SPEED, -SEARCH_TURN_SPEED, self._claw)

        # ── APPROACH_BALL ────────────────────────────────────────
        elif self._state == "APPROACH_BALL":
            if t is not None and t["w"] >= BALL_CAPTURE_WIDTH:
                # Ball is large enough — begin capture
                self._transition("CAPTURE")
            elif t is None and time.monotonic() - self._last_seen > APPROACH_LOST_SEC:
                # Lost ball for too long — go back to search
                self._transition("SEARCH_BALL")
            else:
                self._steer(t, self._claw)

        # ── CAPTURE ──────────────────────────────────────────────
        elif self._state == "CAPTURE":
            elapsed = self._elapsed()

            if elapsed < CAPTURE_OPEN_SEC:
                # Phase 1: stop and open claw
                self._claw = False
                self._stop(self._claw)

            elif elapsed < CAPTURE_OPEN_SEC + CAPTURE_DRIVE_SEC:
                # Phase 2: drive forward slowly with claw open
                self._claw = False
                self._send_cmd(self.approach_speed, self.approach_speed, self._claw)

            elif elapsed < CAPTURE_OPEN_SEC + CAPTURE_DRIVE_SEC + CAPTURE_CLOSE_SEC:
                # Phase 3: close claw and stop
                self._claw = True
                self._stop(self._claw)

            else:
                # Capture complete — search for mat
                self._transition("SEARCH_MAT")

        # ── SEARCH_MAT ───────────────────────────────────────────
        elif self._state == "SEARCH_MAT":
            if t is not None:
                self._transition("APPROACH_MAT")
            else:
                self._send_cmd(SEARCH_TURN_SPEED, -SEARCH_TURN_SPEED, self._claw)

        # ── APPROACH_MAT ─────────────────────────────────────────
        elif self._state == "APPROACH_MAT":
            if t is not None and t["w"] >= MAT_DEPOSIT_WIDTH:
                self._transition("DEPOSIT")
            elif t is None and time.monotonic() - self._last_seen > APPROACH_LOST_SEC:
                self._transition("SEARCH_MAT")
            else:
                self._steer(t, self._claw)

        # ── DEPOSIT ──────────────────────────────────────────────
        elif self._state == "DEPOSIT":
            elapsed = self._elapsed()

            if elapsed < DEPOSIT_OPEN_SEC:
                # Open claw and stop
                self._claw = False
                self._stop(self._claw)

            elif elapsed < DEPOSIT_OPEN_SEC + DEPOSIT_BACK_SEC:
                # Back up slowly
                spd = self.approach_speed
                self._send_cmd(-spd, -spd, self._claw)

            else:
                # Task complete
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
        return rclpy.node.SetParametersResult(successful=True)


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
