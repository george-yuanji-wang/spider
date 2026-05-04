"""
Motor node.

Single source of serial output — nothing else writes to the hardware.

Subscribes:
    spider/ctrl     std_msgs/String     JSON ctrl from bridge
    path/cmd        std_msgs/String     "left,right" from path planner

Decision priority:
    1. Not armed          → STOP
    2. Armed + manual     → use input_left, input_right from ctrl
    3. Armed + auto       → use left, right from path/cmd

Speed from ctrl is always available to both modes for future scaling.

TODO:
    _connect_serial()  — open serial port to motor controller
    _send_serial()     — encode and write motor command
    STOP_SIGNAL        — define correct stop bytes for your protocol
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json


SERIAL_PORT  = '/dev/ttyUSB0'
SERIAL_BAUD  = 115200

# TODO: define correct stop values for your motor controller protocol
STOP_LEFT    = 0
STOP_RIGHT   = 0
STOP_SPEED   = 0


class MotorNode(Node):

    def __init__(self):
        super().__init__('motor_node')

        self._armed       = False
        self._mode        = 'manual'
        self._input_left  = 0
        self._input_right = 0
        self._speed       = 50
        self._auto_left   = 0
        self._auto_right  = 0

        self._serial = None
        self._connect_serial()

        self.create_subscription(String, 'spider/ctrl', self._on_ctrl,     10)
        self.create_subscription(String, 'path/cmd',    self._on_path_cmd, 10)

        # Output timer — 20Hz is sufficient for motor control
        self.create_timer(1.0 / 20.0, self._output)

        self.get_logger().info('Motor node ready')

    # ── Serial ───────────────────────────────────────────────────

    def _connect_serial(self):
        """
        TODO: open serial connection.
            import serial
            self._serial = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        """
        pass

    def _send_serial(self, left: int, right: int, speed: int):
        """
        TODO: encode and transmit motor command.
        left, right : -100 to 100
        speed       : 0 to 100

        Example:
            packet = f'L{left:+04d}R{right:+04d}S{speed:03d}\\n'
            self._serial.write(packet.encode())
        """
        pass

    # ── Subscribers ──────────────────────────────────────────────

    def _on_ctrl(self, msg: String):
        try:
            d = json.loads(msg.data)
            self._armed       = bool(d.get('armed',       False))
            self._mode        = str(d.get('mode',        'manual'))
            self._input_left  = int(d.get('input_left',  0))
            self._input_right = int(d.get('input_right', 0))
            self._speed       = int(d.get('speed',       50))
            self._claw        = bool(d.get('claw',        False))
        except (json.JSONDecodeError, ValueError) as e:
            self.get_logger().warn(f'Malformed spider/ctrl: {e}')

    def _on_path_cmd(self, msg: String):
        try:
            parts            = msg.data.strip().split(',')
            self._auto_left  = int(float(parts[0]))
            self._auto_right = int(float(parts[1]))
        except (ValueError, IndexError) as e:
            self.get_logger().warn(f'Malformed path/cmd: {e}')

    # ── Output ───────────────────────────────────────────────────

    def _output(self):
        claw_val = 1 if self._claw else 0
        
        if not self._armed:
            self._send_serial(STOP_LEFT, STOP_RIGHT, STOP_SPEED)
            return

        if self._mode == 'manual':
            self._send_serial(
                self._input_left,
                self._input_right,
                self._speed,
            )
            return

        if self._mode == 'auto':
            # TODO: decide whether speed should scale auto cmd values
            self._send_serial(
                self._auto_left,
                self._auto_right,
                self._speed,
            )
            return

    def destroy_node(self):
        self._send_serial(STOP_LEFT, STOP_RIGHT, STOP_SPEED)
        # TODO: self._serial.close()
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


if __name__ == '__main__':
    main()