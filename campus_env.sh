# source in T1 (and any terminal running gzclient) before launching Gazebo [house world]
for f in /usr/share/gazebo/setup.sh /usr/share/gazebo-11/setup.sh; do [ -f $f ] && . $f && break; done
export GAZEBO_MODEL_DATABASE_URI=""
_H=$HOME/limo_ws/src/aws-robomaker-small-house-world
export GAZEBO_MODEL_PATH=$_H/models:$_H/fuel_models:$HOME/limo_ws/src/limo_gazebosim/models:/usr/share/gazebo-11/models
