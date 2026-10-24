#!/bin/bash
# demo.sh : full demo = sim + Nav2 (exact mode) + Gazebo window + voice guide
bash ~/start_stack.sh static || exit 1
bash ~/view.sh
source ~/env.sh
python3 ~/limo_ws/guide/voice_guide.py "$@"
