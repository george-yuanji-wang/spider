import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
from cv_bridge import CvBridge
import cv2
import numpy as np
import time


class BallTrackNode(Node):
    def __init__(self):
        super().__init__('ball_track')

        self.declare_parameter('hue_low',     90)
        self.declare_parameter('hue_high',   115)
        self.declare_parameter('sat_low',     80)
        self.declare_parameter('sat_high',   255)
        self.declare_parameter('val_low',     80)
        self.declare_parameter('val_high',   255)
        self.declare_parameter('min_radius',   8)
        self.declare_parameter('blur_kernel',  7)
        self.declare_parameter('erode_iter',   1)
        self.declare_parameter('dilate_iter',  1)

        self._load_params()

        self.bridge  = CvBridge()
        self.sub     = self.create_subscription(Image, 'camera/image_raw', self._callback, 10)
        self.pub     = self.create_publisher(String,  'ball',     10)
        self.fps_pub = self.create_publisher(Float32, 'ball/fps', 10)
        self.add_on_set_parameters_callback(self._on_parameter_change)

        self._frame_times: list[float] = []
        self.fps_timer = self.create_timer(1.0, self._publish_fps)

        self.get_logger().info('ball_track node ready')

    def _load_params(self):
        self.hue_low     = self.get_parameter('hue_low').value
        self.hue_high    = self.get_parameter('hue_high').value
        self.sat_low     = self.get_parameter('sat_low').value
        self.sat_high    = self.get_parameter('sat_high').value
        self.val_low     = self.get_parameter('val_low').value
        self.val_high    = self.get_parameter('val_high').value
        self.min_radius  = self.get_parameter('min_radius').value
        self.blur_kernel = self.get_parameter('blur_kernel').value
        self.erode_iter  = self.get_parameter('erode_iter').value
        self.dilate_iter = self.get_parameter('dilate_iter').value

    def _callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        k       = self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1
        blurred = cv2.GaussianBlur(frame, (k, k), 0)
        hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        lower = np.array([self.hue_low,  self.sat_low,  self.val_low])
        upper = np.array([self.hue_high, self.sat_high, self.val_high])
        mask  = cv2.inRange(hsv, lower, upper)
        mask  = cv2.erode(mask,  None, iterations=self.erode_iter)
        mask  = cv2.dilate(mask, None, iterations=self.dilate_iter)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        out = String()

        if len(cnts) == 0:
            out.data = 'none'
            self.pub.publish(out)
            return

        c                  = max(cnts, key=cv2.contourArea)
        ((cx, cy), radius) = cv2.minEnclosingCircle(c)

        if radius < self.min_radius:
            out.data = 'none'
            self.pub.publish(out)
            return

        x, y, w, h = cv2.boundingRect(c)
        cx, cy     = int(cx), int(cy)

        out.data = f'{cx},{cy},{x},{y},{w},{h}'
        self.pub.publish(out)

        self._frame_times.append(time.monotonic())

    def _publish_fps(self):
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        msg      = Float32()
        msg.data = float(len(self._frame_times))
        self.fps_pub.publish(msg)

    def _on_parameter_change(self, params: list[Parameter]):
        for p in params:
            if hasattr(self, p.name):
                setattr(self, p.name, p.value)
        return rclpy.node.SetParametersResult(successful=True)


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