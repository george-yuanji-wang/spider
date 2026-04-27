import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import threading


class BallDisplayNode(Node):
    def __init__(self):
        super().__init__('ball_display')

        self.bridge = CvBridge()
        self.latest_frame = None
        self.ball_data = None
        self.lock = threading.Lock()

        self.create_subscription(Image, 'camera/image_raw', self._image_callback, 10)
        self.create_subscription(String, 'ball', self._ball_callback, 10)

        self.timer = self.create_timer(1.0 / 30.0, self._display_callback)

        self.get_logger().info('ball_display node ready')

    def _image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        with self.lock:
            self.latest_frame = frame

    def _ball_callback(self, msg):
        with self.lock:
            self.ball_data = msg.data

    def _display_callback(self):
        with self.lock:
            frame = self.latest_frame.copy() if self.latest_frame is not None else None
            ball = self.ball_data

        if frame is None:
            return

        if ball and ball != 'none':
            try:
                cx, cy, x, y, w, h = map(int, ball.split(','))
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
                arm = 8
                cv2.line(frame, (cx - arm, cy), (cx + arm, cy), (255, 255, 255), 2)
                cv2.line(frame, (cx, cy - arm), (cx, cy + arm), (255, 255, 255), 2)
            except (ValueError, TypeError):
                pass

        cv2.imshow('Ball Display', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.get_logger().info('Display closed')
            cv2.destroyAllWindows()

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BallDisplayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()