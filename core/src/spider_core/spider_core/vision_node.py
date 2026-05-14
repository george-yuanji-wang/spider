"""
vision_node

Dual-mode vision — detects blue ball OR red mat depending on detect_mode parameter.
Switched by auto_node via ros2 param set.

Publishes:
    vision/target       std_msgs/String     "cx,cy,x,y,w,h" or "none"
    vision/fps          std_msgs/Float32    rolling FPS

Parameters:
    detect_mode         string              "ball" or "mat"
    hue_low / hue_high  int                 ball HSV (blue)
    sat_low / sat_high  int
    val_low / val_high  int
    mat_hue_low2        int                 red mat wraps around hue=0
    mat_hue_high2       int
    mat_sat_low         int
    mat_val_low         int
    min_radius          int
    blur_kernel         int
    dilate_iter         int
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
from cv_bridge import CvBridge
import cv2
import numpy as np
import time


class VisionNode(Node):

    def __init__(self):
        super().__init__("vision_node")

        # ── Ball (blue) params ───────────────────────────────────
        self.declare_parameter("detect_mode",  "ball")
        self.declare_parameter("hue_low",      90)
        self.declare_parameter("hue_high",     115)
        self.declare_parameter("sat_low",      80)
        self.declare_parameter("sat_high",     255)
        self.declare_parameter("val_low",      80)
        self.declare_parameter("val_high",     255)

        # ── Mat (red) params — red wraps around hue 0 ────────────
        # Red lives at 0-10 AND 170-179 in HSV
        self.declare_parameter("mat_hue_low1",  0)
        self.declare_parameter("mat_hue_high1", 10)
        self.declare_parameter("mat_hue_low2",  170)
        self.declare_parameter("mat_hue_high2", 179)
        self.declare_parameter("mat_sat_low",   80)
        self.declare_parameter("mat_val_low",   50)

        # ── Shared detection params ──────────────────────────────
        self.declare_parameter("min_radius",   8)
        self.declare_parameter("blur_kernel",  7)
        self.declare_parameter("dilate_iter",  1)
        self.declare_parameter("erode_iter",   1)

        self._load_params()

        self.bridge  = CvBridge()
        self.sub     = self.create_subscription(
            Image, "camera/image_raw", self._callback, 10
        )
        self.pub     = self.create_publisher(String,  "vision/target", 10)
        self.fps_pub = self.create_publisher(Float32, "vision/fps",    10)

        self.add_on_set_parameters_callback(self._on_param_change)

        self._frame_times: list[float] = []
        self.create_timer(1.0, self._publish_fps)

        self.get_logger().info(f"Vision node ready — mode: {self.detect_mode}")

    def _load_params(self):
        self.detect_mode   = self.get_parameter("detect_mode").value
        self.hue_low       = self.get_parameter("hue_low").value
        self.hue_high      = self.get_parameter("hue_high").value
        self.sat_low       = self.get_parameter("sat_low").value
        self.sat_high      = self.get_parameter("sat_high").value
        self.val_low       = self.get_parameter("val_low").value
        self.val_high      = self.get_parameter("val_high").value
        self.mat_hue_low1  = self.get_parameter("mat_hue_low1").value
        self.mat_hue_high1 = self.get_parameter("mat_hue_high1").value
        self.mat_hue_low2  = self.get_parameter("mat_hue_low2").value
        self.mat_hue_high2 = self.get_parameter("mat_hue_high2").value
        self.mat_sat_low   = self.get_parameter("mat_sat_low").value
        self.mat_val_low   = self.get_parameter("mat_val_low").value
        self.min_radius    = self.get_parameter("min_radius").value
        self.blur_kernel   = self.get_parameter("blur_kernel").value
        self.dilate_iter   = self.get_parameter("dilate_iter").value
        self.erode_iter    = self.get_parameter("erode_iter").value

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        k       = self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1
        blurred = cv2.GaussianBlur(frame, (k, k), 0)
        hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        if self.detect_mode == "ball":
            mask = self._ball_mask(hsv)
        else:
            mask = self._mat_mask(hsv)

        mask = cv2.erode(mask,  None, iterations=self.erode_iter)
        mask = cv2.dilate(mask, None, iterations=self.dilate_iter)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        out = String()

        if not cnts:
            out.data = "none"
            self.pub.publish(out)
            return

        c                  = max(cnts, key=cv2.contourArea)
        ((cx, cy), radius) = cv2.minEnclosingCircle(c)

        if radius < self.min_radius:
            out.data = "none"
            self.pub.publish(out)
            return

        x, y, w, h = cv2.boundingRect(c)
        out.data   = f"{int(cx)},{int(cy)},{x},{y},{w},{h}"
        self.pub.publish(out)

        self._frame_times.append(time.monotonic())

    def _ball_mask(self, hsv: np.ndarray) -> np.ndarray:
        lower = np.array([self.hue_low, self.sat_low, self.val_low])
        upper = np.array([self.hue_high, self.sat_high, self.val_high])
        return cv2.inRange(hsv, lower, upper)

    def _mat_mask(self, hsv: np.ndarray) -> np.ndarray:
        # Red wraps around — combine two ranges
        lower1 = np.array([self.mat_hue_low1, self.mat_sat_low, self.mat_val_low])
        upper1 = np.array([self.mat_hue_high1, 255, 255])
        lower2 = np.array([self.mat_hue_low2, self.mat_sat_low, self.mat_val_low])
        upper2 = np.array([self.mat_hue_high2, 255, 255])
        return cv2.bitwise_or(
            cv2.inRange(hsv, lower1, upper1),
            cv2.inRange(hsv, lower2, upper2),
        )

    def _publish_fps(self):
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        msg      = Float32()
        msg.data = float(len(self._frame_times))
        self.fps_pub.publish(msg)

    def _on_param_change(self, params: list[Parameter]):
        for p in params:
            if hasattr(self, p.name):
                setattr(self, p.name, p.value)
                self.get_logger().info(f"Param updated: {p.name} = {p.value}")
        return rclpy.node.SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()