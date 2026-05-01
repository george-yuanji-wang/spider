#!/bin/bash

# ── Spider Studio run script ──────────────────────────────────────
# Usage:
#   ./run.sh          launch all ROS nodes
#   ./run.sh --gui    launch ROS nodes + Next.js GUI
#   ./run.sh --stop   kill everything

set -e

WS_DIR="$HOME/ros2_ws"
GUI_DIR="$(cd "$(dirname "$0")/gui" && pwd)"
LOG_DIR="$(cd "$(dirname "$0")" && pwd)/logs"

mkdir -p "$LOG_DIR"

stop_all() {
    echo "[spider] Stopping all nodes..."
    pkill -f "spider_core" 2>/dev/null || true
    pkill -f "bridge_node" 2>/dev/null || true
    pkill -f "next dev"    2>/dev/null || true
    pkill -f "next start"  2>/dev/null || true
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

# ── Launch ROS nodes ─────────────────────────────────────────────
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

echo "[spider] Starting bridge_node..."
ros2 run spider_core bridge_node \
    > "$LOG_DIR/bridge.log" 2>&1 &

echo "[spider] All ROS nodes launched. Logs in $LOG_DIR/"

# ── Optionally launch GUI ────────────────────────────────────────
if [ "$1" == "--gui" ]; then
    echo "[spider] Starting Next.js GUI..."
    cd "$GUI_DIR"
    npm start > "$LOG_DIR/gui.log" 2>&1 &
    echo "[spider] GUI launched at http://localhost:3000"
fi

echo "[spider] System running. Use ./run.sh --stop to shut down."

# Keep script alive so CTRL+C kills everything
trap stop_all INT
wait