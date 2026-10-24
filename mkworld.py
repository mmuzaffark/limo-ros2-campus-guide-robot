import os
W = os.path.expanduser('~/limo_ws/src/aws-robomaker-small-house-world/worlds/small_house.world')
s = open(W).read()
blk = ("  <plugin name='gazebo_ros_state' filename='libgazebo_ros_state.so'>\n"
       "    <ros><namespace>/gazebo</namespace></ros>\n"
       "    <update_rate>10.0</update_rate>\n  </plugin>\n")
print('</world> count:', s.count('</world>'))
if s.count('</world>') == 1 and 'gazebo_ros_state' not in s:
    s = s.replace('</world>', blk + '</world>')
open(os.path.expanduser('~/limo_ws/worlds_local/house_state.world'), 'w').write(s)
print('wrote house_state.world')
