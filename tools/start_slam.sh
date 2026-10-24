#!/bin/bash
# start_slam.sh : sim + SLAM Toolbox + Nav2 (navigation only, no map server, no AMCL, no static TF)
source ~/env.sh; cd ~
~/cleanup.sh >/dev/null 2>&1
nohup ros2 launch limo_gazebosim limo_gazebo_warehouse.launch.py headless:=True world:=$HOME/limo_ws/worlds_local/mini_campus.world > ~/sim_run.log 2>&1 &
for i in $(seq 1 60); do grep -q "Successfully spawned" ~/sim_run.log && break; sleep 2; done
grep -q "Successfully spawned" ~/sim_run.log && echo "sim: robot spawned" || { echo "sim: spawn FAILED, see ~/sim_run.log"; exit 1; }
sleep 15
nohup ros2 launch slam_toolbox online_async_launch.py slam_params_file:=$HOME/limo_ws/params/slam_campus.yaml use_sim_time:=true > ~/slam_run.log 2>&1 &
for i in $(seq 1 30); do ros2 topic list 2>/dev/null | grep -qx /map && break; sleep 2; done
ros2 topic list 2>/dev/null | grep -qx /map && echo "slam: /map is publishing" || { echo "slam: no /map, see ~/slam_run.log"; exit 1; }
nohup ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true use_composition:=False params_file:=$HOME/limo_ws/params/nav2_campus.yaml > ~/nav2_run.log 2>&1 &
for i in $(seq 1 60); do grep -q "Managed nodes are active" ~/nav2_run.log && break; sleep 2; done
grep -q "Managed nodes are active" ~/nav2_run.log && echo "nav2: active (navigation only)" || { echo "nav2: NOT active, see ~/nav2_run.log"; exit 1; }
