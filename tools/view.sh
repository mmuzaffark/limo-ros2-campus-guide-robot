#!/bin/bash
# view.sh : open the Gazebo window on the running simulation (camera looks over the campus)
source ~/env.sh
export GAZEBO_MODEL_PATH=$HOME/limo_ws/src/limo_gazebosim/models:/usr/share/gazebo-11/models
mkdir -p ~/.gazebo; printf '[geometry]\nx=80\ny=60\nwidth=1400\nheight=860\n' > ~/.gazebo/gui.ini
pkill -f gzclient; sleep 1
nohup gzclient > ~/gzclient.log 2>&1 &
echo "gzclient started (pid $!)"
