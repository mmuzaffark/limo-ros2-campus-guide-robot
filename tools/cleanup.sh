pkill -9 -f "gzserver|gzclient|spawn_entity|component_container|nav2|amcl|map_server|lifecycle_manager|bt_navigator|controller_server|planner_server|behavior_server|smoother_server|waypoint_follower|velocity_smoother|robot_state_publisher|joint_state_publisher|twist_watchdog|teleop|static_transform_publisher|slam_toolbox|explore_lite"
ros2 daemon stop; sleep 2
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null
echo "leftovers (should be empty):"; pgrep -af "gz|nav2|amcl|map_server|lifecycle|ros2" | head
ros2 daemon start
