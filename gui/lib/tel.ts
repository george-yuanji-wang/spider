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
  ball:           Ball | null;
  path:           PathPoint[];
}

export const defaultTel: Tel = {
  connected:      false,
  camera_status:  false,
  motor_status:   false,
  tracker_status: false,
  planner_status: false,
  stream_status: false,
  camera_fps:     0,
  tracker_fps:    0,
  planner_fps:    0,
  ball: {
    cx: 320, cy: 240, x: 270, y: 190, w: 100, h: 100,
  },
  path: [
    { x: 50,  y: 50  },
    { x: 150, y: 200 },
    { x: 300, y: 150 },
    { x: 500, y: 400 },
  ],
};