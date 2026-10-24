#!/bin/bash
# demo_slam.sh : one-command demo on the robot's own SLAM map (AMCL + Pure Pursuit)
# Opens: Gazebo window, RViz2 (Nav2 view), guide GUI.  NO_RVIZ=1 skips RViz.
source ~/env.sh; cd ~
export MAP=$HOME/limo_ws/maps/campus_slam.yaml
export PARAMS=$HOME/limo_ws/params/nav2_campus_rpp.yaml
RVIZ_CFG=/opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
for f in "$MAP" "$PARAMS" ~/limo_gui.py ~/view.sh "$RVIZ_CFG"; do
  [ -f "$f" ] || { echo "missing: $f"; exit 1; }
done
pkill -f rviz2 2>/dev/null
echo "== starting simulation + Nav2 (SLAM map, AMCL, Pure Pursuit) =="
bash ~/start_stack.sh loc || { echo "stack failed: see ~/sim_run.log and ~/nav2_run.log"; exit 1; }
echo "== opening Gazebo window =="
nohup bash ~/view.sh > ~/view_run.log 2>&1 &
sleep 5
if [ -z "$NO_RVIZ" ]; then
  echo "== opening RViz2 =="
  nohup rviz2 -d "$RVIZ_CFG" --ros-args -p use_sim_time:=true > ~/rviz_run.log 2>&1 &
  sleep 5
fi
echo "== opening guide GUI (close the window to finish) =="
python3 ~/limo_gui.py
read -r -p "Stop the simulation now? [Y/n] " a
case "$a" in
  [nN]*) echo "left running; stop later with: pkill -f rviz2; bash ~/cleanup.sh";;
  *) pkill -f rviz2 2>/dev/null; bash ~/cleanup.sh >/dev/null 2>&1; echo "stopped";;
esac
