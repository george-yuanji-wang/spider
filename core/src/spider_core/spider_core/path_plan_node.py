"""
Path planning node — placeholder.

Subscribes:
    ball            std_msgs/String     "cx,cy,x,y,w,h" or "none"

Publishes:
    path            std_msgs/String     JSON [{x,y}, ...]
    path/fps        std_msgs/Float32    rolling FPS
    path/cmd        std_msgs/String     "left,right" motor command for auto mode

TODO:
    _compute_path()      — real planning algorithm
    _compute_motor_cmd() — real controller (e.g. proportional, pure pursuit)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
import json
import time


class PathPlanNode(Node):

    def __init__(self):
        super().__init__('path_plan')

        # TODO: declare planning parameters here as algorithm is defined
        # e.g. self.declare_parameter('lookahead_dist', 50)

        self.sub = self.create_subscription(
            String, 'ball', self._on_ball, 10
        )
        self.path_pub = self.create_publisher(String,  'path',     10)
        self.fps_pub  = self.create_publisher(Float32, 'path/fps', 10)
        self.cmd_pub  = self.create_publisher(String,  'path/cmd', 10)

        self._frame_times: list[float] = []
        self.create_timer(1.0, self._publish_fps)

        self.get_logger().info('path_plan node ready (placeholder)')

    def _on_ball(self, msg: String):
        raw = msg.data.strip()

        if raw in ('none', ''):
            self._publish_empty()
            return

        try:
            cx, cy, x, y, w, h = [float(v) for v in raw.split(',')]
            ball = {'cx': cx, 'cy': cy, 'x': x, 'y': y, 'w': w, 'h': h}
        except ValueError:
            self.get_logger().warn(f'Malformed /ball: {raw}')
            self._publish_empty()
            return

        path        = self._compute_path(ball)
        left, right = self._compute_motor_cmd(ball)

        path_msg      = String()
        path_msg.data = json.dumps(path)
        self.path_pub.publish(path_msg)

        cmd_msg      = String()
        cmd_msg.data = f'{left},{right}'
        self.cmd_pub.publish(cmd_msg)

        self._frame_times.append(time.monotonic())

    def _compute_path(self, ball: dict) -> list[dict]:
        """
        TODO: replace with real path planning.
        Returns list of {x, y} waypoints.
        Dummy: straight line from bottom-centre to ball.
        """
        return [
            {'x': 320.0, 'y': 480.0},
            {'x': ball['cx'], 'y': ball['cy']},
        ]

    def _compute_motor_cmd(self, ball: dict) -> tuple[int, int]:
        """
        TODO: replace with real controller output.
        Returns (left, right) in range -100 to 100.
        """
        return 0, 0

    def _publish_empty(self):
        path_msg      = String()
        path_msg.data = json.dumps([])
        self.path_pub.publish(path_msg)

        cmd_msg      = String()
        cmd_msg.data = '0,0'
        self.cmd_pub.publish(cmd_msg)

    def _publish_fps(self):
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        msg      = Float32()
        msg.data = float(len(self._frame_times))
        self.fps_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PathPlanNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()