from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dataclasses import asdict
from typing import Optional
from bridge import state

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request models ──
class CtrlPayload(BaseModel):
    armed:       bool
    mode:        str
    input_left:  int
    input_right: int
    speed:       int

class BallParamsPayload(BaseModel):
    hue_low:     int
    hue_high:    int
    sat_low:     int
    sat_high:    int
    val_low:     int
    val_high:    int
    min_radius:  int
    blur_kernel: int
    dilate_iter: int

class ParamsPayload(BaseModel):
    ball: BallParamsPayload

# ── Health ──
@app.get("/api/health")
def health():
    return {"ok": True}

# ── Telemetry ──
@app.get("/api/tel")
def get_tel():
    return asdict(state.tel)

# ── Ctrl ──
@app.post("/api/ctrl")
def post_ctrl(payload: CtrlPayload):
    state.ctrl.armed       = payload.armed
    state.ctrl.mode        = payload.mode
    state.ctrl.input_left  = payload.input_left
    state.ctrl.input_right = payload.input_right
    state.ctrl.speed       = payload.speed
    return {"ok": True}

# ── Params ──
@app.post("/api/params")
def post_params(payload: ParamsPayload):
    b = payload.ball
    state.ball_params.hue_low     = b.hue_low
    state.ball_params.hue_high    = b.hue_high
    state.ball_params.sat_low     = b.sat_low
    state.ball_params.sat_high    = b.sat_high
    state.ball_params.val_low     = b.val_low
    state.ball_params.val_high    = b.val_high
    state.ball_params.min_radius  = b.min_radius
    state.ball_params.blur_kernel = b.blur_kernel
    state.ball_params.dilate_iter = b.dilate_iter
    state.add_cli(f"Ball params updated — H:{b.hue_low}-{b.hue_high} S:{b.sat_low}-{b.sat_high} V:{b.val_low}-{b.val_high}")
    return {"ok": True}

# ── CLI ──
@app.get("/api/cli")
def get_cli():
    return {"messages": state.cli_buffer}