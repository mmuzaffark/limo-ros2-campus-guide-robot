c=$(ros2 topic echo /clock --once --field clock.sec | head -1)
t=$(timeout -s INT 4 ros2 run tf2_ros tf2_echo map odom 2>&1 | grep "At time" | tail -1 | awk '{print $3}')
echo "clock $c | map->odom ${t:-NONE}"
