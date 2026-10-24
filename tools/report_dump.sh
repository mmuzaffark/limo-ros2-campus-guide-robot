#!/bin/bash
O=~/limo_report_dump.txt; : > $O
s(){ echo -e "\n\n######## $1 ########" >> $O; }
f(){ s "FILE $1"; [ -f "$1" ] && cat "$1" >> $O || echo "(missing)" >> $O; }
P=~/limo_ws/params; M=~/limo_ws/maps
s "SYSTEM"; { lsb_release -d; uname -r; echo "RMW=$RMW_IMPLEMENTATION"; echo "ROS_DISTRO=$ROS_DISTRO"; python3 --version; gazebo --version 2>/dev/null | head -2; nproc; free -h | head -2; } >> $O 2>&1
s "WSL VERSION"; powershell.exe -NoProfile -Command "wsl --version" 2>/dev/null | tr -d '\0' >> $O
s "ROS PACKAGE VERSIONS"; dpkg -l | grep -E "ros-humble-(navigation2|nav2-bringup|nav2-amcl|nav2-regulated|nav2-dwb|nav2-controller|nav2-planner|nav2-navfn|nav2-map-server|slam-toolbox|tf2 |tf2-ros |rclpy |rclcpp |gazebo-ros |gazebo-plugins|gazebo-ros-pkgs|rmw-cyclonedds|rmw-fastrtps-cpp|ros2-control |diff-drive|ros-base|desktop )" | awk '{print $2, $3}' >> $O
s "GAZEBO / OTHER APT"; dpkg -l | grep -E "^ii +(gazebo|libgazebo11|ffmpeg|python3-tk|pulseaudio-utils|espeak)" | awk '{print $2, $3}' >> $O
s "APT UPGRADE HISTORY (ROS)"; { zgrep -h -A3 "Start-Date" /var/log/apt/history.log* 2>/dev/null | grep -E "Start-Date|Upgrade:|Install:" | grep -B1 "ros-humble" | cut -c1-600; } >> $O
s "PIP"; pip3 list 2>/dev/null | grep -iE "faster-whisper|ctranslate2|numpy|scipy|rapidfuzz|pyyaml|pillow|sounddevice|onnxruntime|transforms3d" >> $O
s "WORKSPACE SRC"; ls ~/limo_ws/src >> $O; for d in ~/limo_ws/src/*/; do (cd "$d" 2>/dev/null && git log -1 --format="$(basename $d): %h %cd %s" 2>/dev/null) >> $O; done
for x in nav2_campus_rpp.yaml nav2_campus.yaml nav2_campus_demo.yaml slam_campus.yaml explore_campus.yaml places_campus.yaml goals_campus.txt; do f $P/$x; done
s "DIFF nav2_campus.yaml vs nav2_campus_rpp.yaml"; diff $P/nav2_campus.yaml $P/nav2_campus_rpp.yaml >> $O
s "DIFF stock humble nav2_params vs nav2_campus.yaml"; diff /opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml $P/nav2_campus.yaml >> $O
s "DIFF stock slam params vs slam_campus.yaml"; diff /opt/ros/humble/share/slam_toolbox/config/mapper_params_online_async.yaml $P/slam_campus.yaml >> $O
for x in campus_slam.yaml campus_v1.yaml; do f $M/$x; done
f ~/limo_ws/make_mini_campus.py
for x in env.sh cleanup.sh start_stack.sh start_slam.sh demo_slam.sh view.sh gate2.sh; do f ~/$x; done
s "GUIDE argparse + parser"; grep -nE "add_argument|threshold|def parse|def _score|FILLER|WORDS" ~/limo_ws/guide/guide_manager.py ~/limo_ws/guide/voice_guide.py >> $O
s "LIDAR / CONTROLLER IN URDF/XACRO"; grep -rnE "<ray|samples|min_angle|max_angle|<min>|<max>|resolution|update_rate|four_diff|wheel_separation|wheel_radius|odom|mu1|mu2|libgazebo_ros" ~/limo_ws/src/limo_description ~/limo_ws/src/limo_gazebosim --include=*.xacro --include=*.urdf --include=*.gazebo --include=*.yaml 2>/dev/null | head -80 >> $O
s "LAUNCH FILE USED"; f ~/limo_ws/src/limo_gazebosim/launch/limo_gazebo_warehouse.launch.py
cp $O "/mnt/c/Users/M. Muzaffar Khan/Documents/limo_report_dump.txt" && echo "dump: $(wc -l < $O) lines -> Documents\\limo_report_dump.txt"
