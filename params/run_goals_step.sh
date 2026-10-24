#!/bin/bash
source /opt/ros/humble/setup.bash
TIMEOUT=${TIMEOUT:-90}
n=0; ok=0
while read -r x y z w; do
  n=$((n+1))
  echo "=== goal $n -> ($x, $y)  [$(date +%T)]"
  read -p "Press Enter to send goal $n (Ctrl+C to stop) " < /dev/tty
  start=$(date +%s)
  r=$(timeout -s INT $TIMEOUT ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: map}, pose: {position: {x: $x, y: $y}, orientation: {z: $z, w: $w}}}}" 2>&1 | tail -n 1)
  rc=${PIPESTATUS[0]}
  dur=$(( $(date +%s) - start ))
  [[ -z "$r" ]] && r="NO RESULT (timed out after ${TIMEOUT}s)"
  echo "goal $n: $r  (${dur}s)"
  [[ "$r" == *SUCCEEDED* ]] && ok=$((ok+1))
  pkill -INT -f send_goal 2>/dev/null; sleep 2
done < ~/limo_ws/params/goals.txt
echo "RESULT: $ok/$n succeeded"
