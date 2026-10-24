source /opt/ros/humble/setup.bash
source ~/limo_ws/install/setup.bash
for f in /usr/share/gazebo/setup.sh /usr/share/gazebo-11/setup.sh; do [ -f $f ] && . $f && break; done
export GAZEBO_MODEL_DATABASE_URI=""
go() { ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: $1, y: $2, z: 0.0}, orientation: {z: $3, w: $4}}}}"; }
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
