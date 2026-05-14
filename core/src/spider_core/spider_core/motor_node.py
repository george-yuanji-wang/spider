"""
Motor node.

Subscribes:
    spider/ctrl     std_msgs/String     JSON ctrl from bridge
    path/cmd        std_msgs/String     JSON {"left","right","claw"} from auto_node

Serial protocol to ESP32-C3:
    "left,right,servo,enable\n"
    left:   -100 to 100  (scaled by speed)
    right:  -100 to 100  (scaled by speed)
    servo:  0=closed  1=open
    enable: 0=shutdown  1=run

ESP watchdog: 500ms — we publish at 20Hz (50ms) to keep it alive.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import serial
import serial.tools.list_ports


SERIAL_BAUD      = 115200
SERIAL_TIMEOUT_S = 1.0

STOP_LEFT  = 0
STOP_RIGHT = 0
STOP_SPEED = 0


def _find_port() -> str | None:
    candidates = []
    for p in serial.tools.list_ports.comports():
        if "USB" in p.device or "ACM" in p.device:
            candidates.append(p.device)
    if candidates:
        return sorted(candidates)[0]
    return None


class MotorNode(Node):

    def __init__(self):
        super().__init__("motor_node")

        self._armed       = False
        self._mode        = "manual"
        self._input_left  = 0
        self._input_right = 0
        self._speed       = 50
        self._claw        = False

        self._auto_left   = 0
        self._auto_right  = 0
        self._auto_claw   = False

        self._serial: serial.Serial | None = None
        self._connect_serial()

        self.create_subscription(String, "spider/ctrl", self._on_ctrl,     10)
        self.create_subscription(String, "path/cmd",    self._on_path_cmd, 10)

        self.create_timer(1.0 / 20.0, self._output)

        self.get_logger().info("Motor node ready")

    # ── Serial ───────────────────────────────────────────────────

    def _connect_serial(self):
        port = _find_port()
        if port is None:
            self.get_logger().warn("No serial port found — running without hardware")
            return
        try:
            self._serial = serial.Serial(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT_S)
            self.get_logger().info(f"Serial connected: {port} @ {SERIAL_BAUD}")
        except serial.SerialException as e:
            self.get_logger().error(f"Serial open failed: {e}")
            self._serial = None

    def _send_serial(self, left: int, right: int, speed: int, claw: bool, armed: bool):
        enable = 1 if armed else 0
        scale  = speed / 100.0
        scaled_left  = int(left  * scale)
        scaled_right = int(right * scale)
        servo = 0 if claw else 1   # 0=closed 1=open

        packet = f"{scaled_left},{scaled_right},{servo},{enable}\n"

        print(
            f"[MOTOR] L:{scaled_left:+4d}  R:{scaled_right:+4d}  "
            f"SPD:{speed:3d}  SERVO:{'CLOSED' if claw else 'OPEN  '}  "
            f"EN:{enable}  → {packet.strip()}"
        )

        if self._serial and self._serial.is_open:
            try:
                self._serial.write(packet.encode())
            except serial.SerialException as e:
                self.get_logger().warn(f"Serial write failed: {e}")
                self._serial = None

    # ── Subscribers ──────────────────────────────────────────────

    def _on_ctrl(self, msg: String):
        try:
            d = json.loads(msg.data)
            self._armed       = bool(d.get("armed",       False))
            self._mode        = str(d.get("mode",        "manual"))
            self._input_left  = int(d.get("input_left",  0))
            self._input_right = int(d.get("input_right", 0))
            self._speed       = int(d.get("speed",       50))
            self._claw        = bool(d.get("claw",       False))
        except (json.JSONDecodeError, ValueError) as e:
            self.get_logger().warn(f"Malformed spider/ctrl: {e}")

    def _on_path_cmd(self, msg: String):
        try:
            d = json.loads(msg.data)
            self._auto_left  = int(d.get("left",  0))
            self._auto_right = int(d.get("right", 0))
            self._auto_claw  = bool(d.get("claw", 0))
        except (json.JSONDecodeError, ValueError):
            try:
                # Fallback: old "left,right" plain format
                parts            = msg.data.strip().split(",")
                self._auto_left  = int(float(parts[0]))
                self._auto_right = int(float(parts[1]))
                self._auto_claw  = False
            except (ValueError, IndexError) as e:
                self.get_logger().warn(f"Malformed path/cmd: {e}")

    # ── Output ───────────────────────────────────────────────────

    def _output(self):
        if not self._armed:
            self._send_serial(
                STOP_LEFT, STOP_RIGHT, STOP_SPEED,
                self._claw, armed=False,
            )
            return

        if self._mode == "manual":
            self._send_serial(
                self._input_left,
                self._input_right,
                self._speed,
                self._claw,
                armed=True,
            )
            return

        if self._mode == "auto":
            # In auto mode speed is NOT applied — auto_node sends
            # already-scaled values directly. Pass speed=100 so
            # _send_serial does not double-scale.
            self._send_serial(
                self._auto_left,
                self._auto_right,
                100,
                self._auto_claw,
                armed=True,
            )
            return

    def destroy_node(self):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(b"0,0,1,0\n")
            except Exception:
                pass
            self._serial.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()