#!/bin/bash
# start_stack.sh [static|amcl] : clean start of sim + Nav2 (logs: ~/sim_run.log, ~/nav2_run.log)
MODE=${1:-static}
source ~/env.sh; cd ~
~/cleanup.sh >/dev/null 2>&1
nohup ros2 launch limo_gazebosim limo_gazebo_warehouse.launch.py headless:=True world:=$HOME/limo_ws/worlds_local/mini_campus.world > ~/sim_run.log 2>&1 &
for i in $(seq 1 60); do grep -q "Successfully spawned" ~/sim_run.log && break; sleep 2; done
grep -q "Successfully spawned" ~/sim_run.log && echo "sim: robot spawned" || { echo "sim: spawn FAILED, see ~/sim_run.log"; exit 1; }
sleep 15
if [ "$MODE" = static ]; then
  nohup ros2 run tf2_ros static_transform_publisher --x 0 --y 0 --z 0 --roll 0 --pitch 0 --yaw 0 --frame-id map --child-frame-id odom --ros-args -p use_sim_time:=true > ~/static_tf.log 2>&1 &
  P=$HOME/limo_ws/params/nav2_campus_static.yaml; sleep 3
else
  P=${PARAMS:-$HOME/limo_ws/params/nav2_campus.yaml}
fi
nohup ros2 launch nav2_bringup bringup_launch.py map:=${MAP:-$HOME/limo_ws/maps/campus_v1.yaml} use_sim_time:=true use_composition:=False params_file:=$P > ~/nav2_run.log 2>&1 &
for i in $(seq 1 60); do [ $(grep -c "Managed nodes are active" ~/nav2_run.log) -ge 2 ] && break; sleep 2; done
[ $(grep -c "Managed nodes are active" ~/nav2_run.log) -ge 2 ] && echo "nav2: active ($MODE mode)" || { echo "nav2: NOT active, see ~/nav2_run.log"; exit 1; }
python3 ~/stale.py
