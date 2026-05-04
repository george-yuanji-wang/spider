import json
import os
import threading

STATE_FILE  = "/tmp/spider_state.json"
CTRL_FILE   = "/tmp/spider_ctrl.json"
PARAMS_FILE = "/tmp/spider_params.json"

_lock = threading.Lock()

DEFAULT_STATE = {
    "tel": {
        "connected":      False,
        "camera_status":  False,
        "motor_status":   False,
        "tracker_status": False,
        "planner_status": False,
        "stream_status":  False,
        "camera_fps":     0.0,
        "tracker_fps":    0.0,
        "planner_fps":    0.0,
        "ball":           None,
        "path":           [],
    },
    "cli": [],
}

DEFAULT_CTRL = {
    "armed":       False,
    "mode":        "manual",
    "input_left":  0,
    "input_right": 0,
    "speed":       50,
    "claw":       False,
}

DEFAULT_PARAMS = {
    "ball": {
        "hue_low":     90,
        "hue_high":    115,
        "sat_low":     80,
        "sat_high":    255,
        "val_low":     80,
        "val_high":    255,
        "min_radius":  8,
        "blur_kernel": 7,
        "dilate_iter": 1,
        "dirty":       False,
    }
}


def _read(path: str, default: dict) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(default))


def _write(path: str, data: dict):
    with _lock:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)


def read_state()  -> dict: return _read(STATE_FILE,  DEFAULT_STATE)
def read_ctrl()   -> dict: return _read(CTRL_FILE,   DEFAULT_CTRL)
def read_params() -> dict: return _read(PARAMS_FILE, DEFAULT_PARAMS)

def write_state(data: dict):  _write(STATE_FILE,  data)
def write_ctrl(data: dict):   _write(CTRL_FILE,   data)
def write_params(data: dict): _write(PARAMS_FILE, data)


def add_cli(text: str):
    from datetime import datetime, timezone
    state = read_state()
    state["cli"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text":      text,
    })
    state["cli"] = state["cli"][-500:]
    write_state(state)


def init():
    if not os.path.exists(STATE_FILE):  write_state(DEFAULT_STATE)
    if not os.path.exists(CTRL_FILE):   write_ctrl(DEFAULT_CTRL)
    if not os.path.exists(PARAMS_FILE): write_params(DEFAULT_PARAMS)