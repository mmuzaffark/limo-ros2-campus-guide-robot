#!/bin/bash
source /opt/ros/humble/setup.bash
n=0; ok=0
while read -r x y z w; do
  n=$((n+1))
  r=$(ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: $x, y: $y}, orientation: {z: $z, w: $w}}}}" | tail -n 1)
  echo "goal $n ($x, $y): $r"
  [[ "$r" == *SUCCEEDED* ]] && ok=$((ok+1))
done < ~/limo_ws/params/goals.txt
echo "RESULT: $ok/$n succeeded"
