"""
vision_node

Dual-mode vision — detects blue ball OR red mat.

Ball mode: uses circularity, aspect ratio and fill ratio filters
           to robustly identify a sphere against other blue objects.

Mat mode:  finds the largest contiguous red area. No shape filters.
           Requires largest contour to be significantly bigger than
           the second largest to avoid false positives.
"""

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


# ── Mat dominance threshold ───────────────────────────────────────
# Largest contour must be this many times bigger than second largest.
# Prevents tracking noise when two similarly-sized red blobs exist.
MAT_DOMINANCE_RATIO = 2.5


class VisionNode(Node):

    def __init__(self):
        super().__init__("vision_node")

        # ── Mode ─────────────────────────────────────────────────
        self.declare_parameter("detect_mode",     "ball")

        # ── Ball (blue) HSV ──────────────────────────────────────
        self.declare_parameter("hue_low",          90)
        self.declare_parameter("hue_high",         106)
        self.declare_parameter("sat_low",          100)
        self.declare_parameter("sat_high",         220)
        self.declare_parameter("val_low",          100)
        self.declare_parameter("val_high",         255)

        # ── Ball shape filters ───────────────────────────────────
        self.declare_parameter("min_radius",       8)
        self.declare_parameter("min_circularity",  0.72)
        self.declare_parameter("min_fill_ratio",   0.60)
        self.declare_parameter("max_aspect_error", 0.30)

        # ── Mat (red) HSV — red wraps around hue 0 ───────────────
        self.declare_parameter("mat_hue_low1",     0)
        self.declare_parameter("mat_hue_high1",    10)
        self.declare_parameter("mat_hue_low2",     170)
        self.declare_parameter("mat_hue_high2",    179)
        self.declare_parameter("mat_sat_low",      80)
        self.declare_parameter("mat_val_low",      50)
        self.declare_parameter("mat_min_area",     2000)  # px² minimum mat size

        # ── Shared pre-processing ────────────────────────────────
        self.declare_parameter("blur_kernel",      7)
        self.declare_parameter("erode_iter",       1)
        self.declare_parameter("dilate_iter",      1)

        self._load_params()

        self.bridge  = CvBridge()
        self.sub     = self.create_subscription(
            Image, "camera/image_raw", self._callback, 10
        )
        self.pub      = self.create_publisher(String,  "vision/target", 10)
        self.fps_pub  = self.create_publisher(Float32, "vision/fps",    10)
        self.mode_pub = self.create_publisher(String,  "vision/mode",   10)

        self.add_on_set_parameters_callback(self._on_param_change)

        self._frame_times: list[float] = []
        self.create_timer(1.0, self._publish_fps)
        self.create_timer(1.0, self._publish_mode)

        self.get_logger().info(f"Vision node ready — mode: {self.detect_mode}")

    def _load_params(self):
        self.detect_mode      = self.get_parameter("detect_mode").value
        self.hue_low          = self.get_parameter("hue_low").value
        self.hue_high         = self.get_parameter("hue_high").value
        self.sat_low          = self.get_parameter("sat_low").value
        self.sat_high         = self.get_parameter("sat_high").value
        self.val_low          = self.get_parameter("val_low").value
        self.val_high         = self.get_parameter("val_high").value
        self.min_radius       = self.get_parameter("min_radius").value
        self.min_circularity  = self.get_parameter("min_circularity").value
        self.min_fill_ratio   = self.get_parameter("min_fill_ratio").value
        self.max_aspect_error = self.get_parameter("max_aspect_error").value
        self.mat_hue_low1     = self.get_parameter("mat_hue_low1").value
        self.mat_hue_high1    = self.get_parameter("mat_hue_high1").value
        self.mat_hue_low2     = self.get_parameter("mat_hue_low2").value
        self.mat_hue_high2    = self.get_parameter("mat_hue_high2").value
        self.mat_sat_low      = self.get_parameter("mat_sat_low").value
        self.mat_val_low      = self.get_parameter("mat_val_low").value
        self.mat_min_area     = self.get_parameter("mat_min_area").value
        self.blur_kernel      = self.get_parameter("blur_kernel").value
        self.erode_iter       = self.get_parameter("erode_iter").value
        self.dilate_iter      = self.get_parameter("dilate_iter").value

    # ── Main callback ─────────────────────────────────────────────

    def _callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

        k       = self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1
        blurred = cv2.GaussianBlur(frame, (k, k), 0) if self.blur_kernel > 1 else frame
        hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        out = String()

        if self.detect_mode == "ball":
            out.data = self._detect_ball(hsv)
        else:
            out.data = self._detect_mat(hsv)

        self.pub.publish(out)
        self._frame_times.append(time.monotonic())

    # ── Ball detection ────────────────────────────────────────────

    def _detect_ball(self, hsv: np.ndarray) -> str:
        lower = np.array([self.hue_low,  self.sat_low,  self.val_low],  dtype=np.uint8)
        upper = np.array([self.hue_high, self.sat_high, self.val_high], dtype=np.uint8)
        mask  = cv2.inRange(hsv, lower, upper)

        if self.erode_iter  > 0: mask = cv2.erode(mask,  None, iterations=self.erode_iter)
        if self.dilate_iter > 0: mask = cv2.dilate(mask, None, iterations=self.dilate_iter)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return "none"

        # Check candidates largest first with shape filters
        for c in sorted(cnts, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(c)
            if area <= 0:
                continue

            ((cx, cy), radius) = cv2.minEnclosingCircle(c)
            if radius < self.min_radius:
                continue

            x, y, w, h = cv2.boundingRect(c)

            # Must be roughly square
            aspect_error = abs(1.0 - (w / float(h))) if h > 0 else 999.0
            if aspect_error > self.max_aspect_error:
                continue

            # Must be circle-like
            perimeter = cv2.arcLength(c, True)
            if perimeter <= 0:
                continue
            circularity = 4.0 * np.pi * area / (perimeter * perimeter)
            if circularity < self.min_circularity:
                continue

            # Must fill enclosing circle well
            circle_area = np.pi * radius * radius
            fill_ratio  = area / circle_area if circle_area > 0 else 0.0
            if fill_ratio < self.min_fill_ratio:
                continue

            return f"{int(cx)},{int(cy)},{x},{y},{w},{h}"

        return "none"

    # ── Mat detection ─────────────────────────────────────────────

    def _detect_mat(self, hsv: np.ndarray) -> str:
        # Red wraps around hue 0 — combine both ranges
        lower1 = np.array([self.mat_hue_low1, self.mat_sat_low, self.mat_val_low], dtype=np.uint8)
        upper1 = np.array([self.mat_hue_high1, 255, 255], dtype=np.uint8)
        lower2 = np.array([self.mat_hue_low2, self.mat_sat_low, self.mat_val_low], dtype=np.uint8)
        upper2 = np.array([self.mat_hue_high2, 255, 255], dtype=np.uint8)

        mask = cv2.bitwise_or(
            cv2.inRange(hsv, lower1, upper1),
            cv2.inRange(hsv, lower2, upper2),
        )

        # Larger dilate to merge nearby red regions into one mat blob
        if self.erode_iter  > 0: mask = cv2.erode(mask,  None, iterations=self.erode_iter)
        if self.dilate_iter > 0: mask = cv2.dilate(mask, None, iterations=self.dilate_iter * 2)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return "none"

        # Sort by area descending
        areas = sorted([cv2.contourArea(c) for c in cnts], reverse=True)
        best  = areas[0]

        # Must be large enough to be a mat
        if best < self.mat_min_area:
            return "none"

        # Must be significantly larger than second biggest blob
        # to avoid tracking noise or background objects
        if len(areas) > 1 and areas[1] > 0:
            if best / areas[1] < MAT_DOMINANCE_RATIO:
                return "none"

        # Get the largest contour
        c    = max(cnts, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        cx   = int(x + w / 2)
        cy   = int(y + h / 2)

        return f"{cx},{cy},{x},{y},{w},{h}"

    # ── Publishers ────────────────────────────────────────────────

    def _publish_fps(self):
        now = time.monotonic()
        self._frame_times = [t for t in self._frame_times if now - t <= 1.0]
        msg      = Float32()
        msg.data = float(len(self._frame_times))
        self.fps_pub.publish(msg)

    def _publish_mode(self):
        msg      = String()
        msg.data = self.detect_mode
        self.mode_pub.publish(msg)

    def _on_param_change(self, params: list[Parameter]):
        for p in params:
            if hasattr(self, p.name):
                setattr(self, p.name, p.value)
                self.get_logger().info(f"Param updated: {p.name} = {p.value}")
        return SetParametersResult(successful=True)


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