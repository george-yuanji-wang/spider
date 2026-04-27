#!/bin/bash

source ~/spider/venv/bin/activate

cd ~/spider/core
colcon build --symlink-install

source ~/spider/core/install/setup.bash

echo "Build complete!"
