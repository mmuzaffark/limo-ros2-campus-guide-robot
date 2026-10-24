#!/bin/bash
# usage: ~/sg.sh LABEL X Y QZ QW
source /opt/ros/humble/setup.bash && source ~/limo_ws/install/setup.bash
L=$1; X=$2; Y=$3; QZ=$4; QW=$5
echo "=== $L start $(date +%T)  clock: $(timeout 3 ros2 topic echo /clock --once | grep -m1 sec)"
timeout -s INT 200 ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
 "{pose: {header: {frame_id: map}, pose: {position: {x: $X, y: $Y, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: $QZ, w: $QW}}}}" | grep "Goal finished"
echo "=== $L end $(date +%T)"
echo "too old: $(grep -c 'too old' ~/nav2_run.log)   last tf_watch: $(tail -1 ~/tf_watch.log)"
python3 ~/odo_chk.py
python3 ~/map_vs_world.py
