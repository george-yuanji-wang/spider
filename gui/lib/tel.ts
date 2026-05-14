export interface Ball {
  cx: number | null;
  cy: number | null;
  x:  number | null;
  y:  number | null;
  w:  number | null;
  h:  number | null;
}

export interface PathPoint {
  x: number | null;
  y: number | null;
}

export interface Tel {
  connected:      boolean;
  camera_status:  boolean;
  motor_status:   boolean;
  tracker_status: boolean;
  planner_status: boolean;
  stream_status:  boolean;
  camera_fps:     number;
  tracker_fps:    number;
  planner_fps:    number;
  auto_state:     string;
  detect_mode:    string;
  ball:           Ball | null;
  path:           PathPoint[];
}

export const defaultTel: Tel = {
  connected:      false,
  camera_status:  false,
  motor_status:   false,
  tracker_status: false,
  planner_status: false,
  stream_status:  false,
  camera_fps:     0,
  tracker_fps:    0,
  planner_fps:    0,
  auto_state:     "IDLE",
  detect_mode:    "ball",
  ball:           null,
  path:           [],
};