from dataclasses import dataclass, field, asdict
from typing import Optional
import time

@dataclass
class Ball:
    cx: Optional[float] = None
    cy: Optional[float] = None
    x:  Optional[float] = None
    y:  Optional[float] = None
    w:  Optional[float] = None
    h:  Optional[float] = None

@dataclass
class PathPoint:
    x: Optional[float] = None
    y: Optional[float] = None

@dataclass
class Tel:
    connected:      bool  = True
    camera_status:  bool  = True
    motor_status:   bool  = False
    tracker_status: bool  = True
    planner_status: bool  = False
    camera_fps:     float = 30.0
    tracker_fps:    float = 24.0
    planner_fps:    float = 0.0
    ball:           Optional[dict] = None
    path:           list  = field(default_factory=list)

@dataclass
class Ctrl:
    armed:       bool  = False
    mode:        str   = "manual"
    input_left:  int   = 0
    input_right: int   = 0
    speed:       int   = 50

@dataclass
class BallParams:
    hue_low:     int = 90
    hue_high:    int = 115
    sat_low:     int = 80
    sat_high:    int = 255
    val_low:     int = 80
    val_high:    int = 255
    min_radius:  int = 8
    blur_kernel: int = 7
    dilate_iter: int = 1

@dataclass
class CliMessage:
    timestamp: str = ""
    text:      str = ""

# ── In-memory state ──
tel   = Tel(
    ball=asdict(Ball(cx=320, cy=240, x=270, y=190, w=100, h=100)),
    path=[{"x": 50, "y": 50}, {"x": 150, "y": 200},
          {"x": 300, "y": 150}, {"x": 500, "y": 400}],
)
ctrl        = Ctrl()
ball_params = BallParams()
cli_buffer: list[dict] = [
    {"timestamp": "2025-01-01T06:58:25.000Z", "text": "Bridge started (mock mode)"},
    {"timestamp": "2025-01-01T06:58:26.000Z", "text": "Waiting for ROS environment"},
]

def add_cli(text: str):
    from datetime import datetime, timezone
    cli_buffer.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text":      text,
    })