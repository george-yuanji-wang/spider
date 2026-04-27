import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Header
import cv2
import numpy as np
from cv_bridge import CvBridge


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera')

        self.declare_parameter('device_index', 0)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('frame_id', 'camera_optical_frame')

        self._load_params()

        self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.info_pub  = self.create_publisher(CameraInfo, 'camera/camera_info', 10)

        self.bridge = CvBridge()
        self.cap = None
        self._open_camera()

        self.timer = self.create_timer(1.0 / self.fps, self._capture_callback)
        self.add_on_set_parameters_callback(self._on_parameter_change)

        self.get_logger().info(
            f'Camera node started — /dev/video{self.device_index} '
            f'@ {self.width}x{self.height} {self.fps}fps'
        )

    def _load_params(self):
        self.device_index = self.get_parameter('device_index').value
        self.width        = self.get_parameter('width').value
        self.height       = self.get_parameter('height').value
        self.fps          = self.get_parameter('fps').value
        self.frame_id     = self.get_parameter('frame_id').value

    def _open_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

        self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open /dev/video{self.device_index}')
            return

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS,          self.fps)

        actual_w   = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.get_logger().info(
            f'Opened /dev/video{self.device_index} — '
            f'actual resolution: {actual_w}x{actual_h} @ {actual_fps:.1f}fps'
        )

    def _capture_callback(self):
        if not self.cap or not self.cap.isOpened():
            self.get_logger().warn('Camera not open, skipping frame', throttle_duration_sec=5)
            return

        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('Failed to grab frame', throttle_duration_sec=2)
            return

        stamp = self.get_clock().now().to_msg()
        header = Header(stamp=stamp, frame_id=self.frame_id)

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header = header
        self.image_pub.publish(img_msg)
        self.info_pub.publish(self._build_camera_info(header, frame.shape))

    def _build_camera_info(self, header: Header, shape) -> CameraInfo:
        h, w = shape[:2]
        msg = CameraInfo()
        msg.header = header
        msg.width  = w
        msg.height = h
        msg.distortion_model = 'plumb_bob'
        fx = fy = float(w)
        cx, cy = w / 2.0, h / 2.0
        msg.k = [fx,  0.0, cx,
                 0.0, fy,  cy,
                 0.0, 0.0, 1.0]
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        msg.r = [1.0, 0.0, 0.0,
                 0.0, 1.0, 0.0,
                 0.0, 0.0, 1.0]
        msg.p = [fx,  0.0, cx,  0.0,
                 0.0, fy,  cy,  0.0,
                 0.0, 0.0, 1.0, 0.0]
        return msg

    def _on_parameter_change(self, params: list[Parameter]):
        needs_reopen = False
        result = rclpy.node.SetParametersResult(successful=True)

        for p in params:
            if p.name == 'fps':
                self.fps = p.value
                self.timer.cancel()
                self.timer = self.create_timer(1.0 / self.fps, self._capture_callback)
                self.get_logger().info(f'FPS changed → {self.fps}')
            elif p.name in ('width', 'height', 'device_index'):
                setattr(self, p.name, p.value)
                needs_reopen = True
            elif p.name == 'frame_id':
                self.frame_id = p.value

        if needs_reopen:
            self._open_camera()

        return result

    def destroy_node(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()