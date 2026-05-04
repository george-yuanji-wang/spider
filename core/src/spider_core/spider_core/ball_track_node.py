import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult

from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32

from cv_bridge import CvBridge
import cv2
import numpy as np
import time


class BallTrackNode(Node):
    def __init__(self):
        super().__init__('ball_track')

        # =========================
        # Tuned HSV parameters
        # From your working Python test
        # =========================
        self.declare_parameter('hue_low', 90)
        self.declare_parameter('hue_high', 106)
        self.declare_parameter('sat_low', 100)
        self.declare_parameter('sat_high', 220)
        self.declare_parameter('val_low', 100)
        self.declare_parameter('val_high', 255)

        # =========================
        # Basic tracking parameters
        # =========================
        self.declare_parameter('min_radius', 8)
        self.declare_parameter('blur_kernel', 2)
        self.declare_parameter('erode_iter', 0)
        self.declare_parameter('dilate_iter', 1)

        # =========================
        # Shape filters
        # =========================
        self.declare_parameter('min_circularity', 0.72)
        self.declare_parameter('min_fill_ratio', 0.60)
        self.declare_parameter('max_aspect_error', 0.30)

        self._load_params()

        self.bridge = CvBridge()

        self.sub = self.create_subscription(
            Image,
            'camera/image_raw',
            self._callback,
            10
        )

        self.pub = self.create_publisher(String, 'ball', 10)
        self.fps_pub = self.create_publisher(Float32, 'ball/fps', 10)

        self.add_on_set_parameters_callback(self._on_parameter_change)

        self._frame_times: list[float] = []
        self.fps_timer = self.create_timer(1.0, self._publish_fps)

        self.get_logger().info('ball_track node ready')

    def _load_params(self):
        self.hue_low = self.get_parameter('hue_low').value
        self.hue_high = self.get_parameter('hue_high').value
        self.sat_low = self.get_parameter('sat_low').value
        self.sat_high = self.get_parameter('sat_high').value
        self.val_low = self.get_parameter('val_low').value
        self.val_high = self.get_parameter('val_high').value

        self.min_radius = self.get_parameter('min_radius').value
        self.blur_kernel = self.get_parameter('blur_kernel').value
        self.erode_iter = self.get_parameter('erode_iter').value
        self.dilate_iter = self.get_parameter('dilate_iter').value

        self.min_circularity = self.get_parameter('min_circularity').value
        self.min_fill_ratio = self.get_parameter('min_fill_ratio').value
        self.max_aspect_error = self.get_parameter('max_aspect_error').value

    def _callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        result = self._track_ball(frame)

        out = String()
        out.data = result
        self.pub.publish(out)

        # Count every processed frame, not only successful detections.
        self._frame_times.append(time.monotonic())

    def _track_ball(self, frame) -> str:
        # Same behavior as your debug script:
        # BLUR_KERNEL=2 becomes 3 because GaussianBlur requires an odd kernel.
        k = self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1

        if self.blur_kernel > 1:
            blurred = cv2.GaussianBlur(frame, (k, k), 0)
        else:
            blurred = frame

        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        lower = np.array(
            [self.hue_low, self.sat_low, self.val_low],
            dtype=np.uint8
        )
        upper = np.array(
            [self.hue_high, self.sat_high, self.val_high],
            dtype=np.uint8
        )

        mask = cv2.inRange(hsv, lower, upper)

        if self.erode_iter > 0:
            mask = cv2.erode(mask, None, iterations=self.erode_iter)

        if self.dilate_iter > 0:
            mask = cv2.dilate(mask, None, iterations=self.dilate_iter)

        cnts, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if len(cnts) == 0:
            return 'none'

        # Check candidates largest first, but do not blindly accept the largest.
        # This prevents a large same-color rectangle from winning automatically.
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

        for c in cnts:
            area = cv2.contourArea(c)
            if area <= 0:
                continue

            ((cx, cy), radius) = cv2.minEnclosingCircle(c)

            if radius < self.min_radius:
                continue

            x, y, w, h = cv2.boundingRect(c)

            # Check 1: bounding box should be roughly square.
            aspect = w / float(h) if h > 0 else 999.0
            aspect_error = abs(1.0 - aspect)

            if aspect_error > self.max_aspect_error:
                continue

            # Check 2: contour should be circle-like.
            # Perfect circle is close to 1.0.
            perimeter = cv2.arcLength(c, True)
            if perimeter <= 0:
                continue

            circularity = 4.0 * np.pi * area / (perimeter * perimeter)

            if circularity < self.min_circularity:
                continue

            # Check 3: contour should fill its enclosing circle reasonably well.
            circle_area = np.pi * radius * radius
            fill_ratio = area / circle_area if circle_area > 0 else 0.0

            if fill_ratio < self.min_fill_ratio:
                continue

            cx, cy = int(cx), int(cy)

            return f'{cx},{cy},{x},{y},{w},{h}'

        return 'none'

    def _publish_fps(self):
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]

        msg = Float32()
        msg.data = float(len(self._frame_times))
        self.fps_pub.publish(msg)

    def _on_parameter_change(self, params: list[Parameter]):
        for p in params:
            if hasattr(self, p.name):
                setattr(self, p.name, p.value)

        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = BallTrackNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()