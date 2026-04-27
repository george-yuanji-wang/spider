source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

cleanup() {
    echo "Shutting down nodes..."
    kill $CAMERA_PID $BALL_TRACK_PID $BALL_DISPLAY_PID 2>/dev/null
    wait
    echo "Done"
}
trap cleanup SIGINT SIGTERM

echo "Starting camera..."
ros2 run spider_core camera &
CAMERA_PID=$!
sleep 2

echo "Starting ball_track..."
ros2 run spider_core ball_track &
BALL_TRACK_PID=$!
sleep 1

echo "Starting ball_display..."
ros2 run spider_core ball_display &
BALL_DISPLAY_PID=$!

echo "All nodes running. Press Ctrl+C to stop."
wait