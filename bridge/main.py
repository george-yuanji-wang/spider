from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bridge.shared as shared

shared.init()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CtrlPayload(BaseModel):
    armed:       bool
    mode:        str
    input_left:  int
    input_right: int
    speed:       int
    claw:       bool


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


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tel")
def get_tel():
    return shared.read_state()["tel"]


@app.post("/api/ctrl")
def post_ctrl(payload: CtrlPayload):
    shared.write_ctrl({
        "armed":       payload.armed,
        "mode":        payload.mode,
        "input_left":  payload.input_left,
        "input_right": payload.input_right,
        "speed":       payload.speed,
        "claw":        payload.claw,
    })
    return {"ok": True}


@app.post("/api/params")
def post_params(payload: ParamsPayload):
    b = payload.ball
    shared.write_params({
        "ball": {
            "hue_low":     b.hue_low,
            "hue_high":    b.hue_high,
            "sat_low":     b.sat_low,
            "sat_high":    b.sat_high,
            "val_low":     b.val_low,
            "val_high":    b.val_high,
            "min_radius":  b.min_radius,
            "blur_kernel": b.blur_kernel,
            "dilate_iter": b.dilate_iter,
            "dirty":       True,
        }
    })
    shared.add_cli(
        f"Ball params updated — "
        f"H:{b.hue_low}-{b.hue_high} "
        f"S:{b.sat_low}-{b.sat_high} "
        f"V:{b.val_low}-{b.val_high} "
        f"r:{b.min_radius} k:{b.blur_kernel} d:{b.dilate_iter}"
    )
    return {"ok": True}


@app.get("/api/cli")
def get_cli():
    return {"messages": shared.read_state()["cli"]}