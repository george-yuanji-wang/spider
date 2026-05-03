#!/bin/bash

# ── Spider Studio run script ──────────────────────────────────────
# Usage:
#   ./run.sh          launch all ROS nodes + HTTP server
#   ./run.sh --gui    launch everything + Next.js GUI
#   ./run.sh --stop   kill everything

set -e

SPIDER_DIR="$(cd "$(dirname "$0")" && pwd)"
WS_DIR="$HOME/spider/core"
GUI_DIR="$SPIDER_DIR/gui"
LOG_DIR="$SPIDER_DIR/logs"

mkdir -p "$LOG_DIR"

stop_all() {
    echo "[spider] Stopping all processes..."
    pkill -f "spider_core" 2>/dev/null || true
    pkill -f "bridge.main" 2>/dev/null || true
    pkill -f "next start"  2>/dev/null || true
    pkill -f "next dev"    2>/dev/null || true
    rm -f /tmp/spider_state.json /tmp/spider_ctrl.json /tmp/spider_params.json
    echo "[spider] Done."
    exit 0
}

if [ "$1" == "--stop" ]; then
    stop_all
fi

# ── Source ROS2 workspace ────────────────────────────────────────
echo "[spider] Sourcing ROS2 workspace..."
source /opt/ros/humble/setup.bash
source "$WS_DIR/install/setup.bash"

# ── Start HTTP server (must come before bridge_node) ─────────────
echo "[spider] Starting HTTP server..."
cd "$SPIDER_DIR"
python -m uvicorn bridge.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    > "$LOG_DIR/http.log" 2>&1 &

sleep 1   # give HTTP server time to bind port before ROS nodes start

# ── Launch ROS nodes ─────────────────────────────────────────────
echo "[spider] Starting bridge_node..."
ros2 run spider_core bridge_node \
    > "$LOG_DIR/bridge.log" 2>&1 &

echo "[spider] Starting camera_node..."
ros2 run spider_core camera_node \
    > "$LOG_DIR/camera.log" 2>&1 &

echo "[spider] Starting ball_track_node..."
ros2 run spider_core ball_track_node \
    > "$LOG_DIR/ball_track.log" 2>&1 &

echo "[spider] Starting path_plan_node..."
ros2 run spider_core path_plan_node \
    > "$LOG_DIR/path_plan.log" 2>&1 &

echo "[spider] Starting motor_node..."
ros2 run spider_core motor_node \
    > "$LOG_DIR/motor.log" 2>&1 &

echo "[spider] All processes launched. Logs in $LOG_DIR/"

# ── Optionally launch GUI ────────────────────────────────────────
if [ "$1" == "--gui" ]; then
    echo "[spider] Starting Next.js GUI..."
    cd "$GUI_DIR"
    npm start > "$LOG_DIR/gui.log" 2>&1 &
    echo "[spider] GUI at http://$(hostname).local:3000"
fi

echo "[spider] System running. Use ./run.sh --stop to shut down."

trap stop_all INT
wait