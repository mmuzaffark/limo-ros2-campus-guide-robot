# AgileX Limo Campus Guide Robot (ROS 2 Humble, simulation)

A simulated AgileX Limo that maps a campus autonomously (SLAM Toolbox + explore_lite), then guides a visitor
to a destination chosen by button, text or voice (faster-whisper), waits, and returns home.
Navigation: Nav2 with AMCL and Regulated Pure Pursuit on the robot-built map.
Forked from Kazimbalti/limo_ros2 (original README: README_upstream.md).

## Requirements
Ubuntu 22.04, ROS 2 Humble, Gazebo Classic 11, Nav2, slam_toolbox, rmw_cyclonedds_cpp,
Python: faster-whisper, rapidfuzz, numpy, pyyaml, pillow; ffmpeg, python3-tk.

## Setup
    git clone <this repo> ~/limo_ws
    cd ~/limo_ws/src && git clone https://github.com/robo-friends/m-explore-ros2.git
    cd ~/limo_ws && rosdep install --from-paths src --ignore-src -r -y && colcon build --symlink-install
    cp tools/*.sh tools/*.py ~/          # scripts expect to run from the home folder
    python3 make_mini_campus.py && python3 ~/add_labels.py

## Run
    source ~/env.sh
    bash ~/demo_slam.sh                  # sim + Nav2 (SLAM map) + Gazebo + RViz2 + guide GUI
    bash ~/start_slam.sh                 # autonomous mapping, then run explore_lite (see docs)

## Layout
guide/ guide logic and voice front-end · tools/ launch, test and GUI scripts · params/ Nav2, SLAM, explore,
places · maps/ exact and SLAM maps · worlds_local/ generated world · clips/ voice commands · docs/ report

Note: roof-label textures are referenced by absolute path (/home/muzaffar/limo_ws/labels); rerun
add_labels.py after cloning to another user account.

## Real-robot implementation
The AgileX Limo Pro lab implementation (Foxy, Nav2, guide manager, Windows GUI, logs and results) is in https://github.com/mmuzaffark/limo-pro-lab-guide-robot

