#!/usr/bin/env bash
set -u
source /opt/ros/humble/setup.bash
A=$HOME/limo_ws/archive_$(date +%Y%m%d_%H%M)
P=$HOME/limo_ws/params
mkdir -p "$A/params" "$A/logs"

# stop everything
pkill -9 -f "gzserver|gzclient|spawn_entity|rviz2|teleop|component_container|static_transform|amcl|map_server|run_goals_step|send_goal|ros2 launch"
sleep 2
ros2 daemon stop >/dev/null 2>&1
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null     # stale DDS shared memory only

# archive params (keep goals.txt and the scorer) and logs
for f in "$P"/*; do
  case "$(basename "$f")" in goals.txt|run_goals_step.sh) ;; *) mv -- "$f" "$A/params/" ;; esac
done
for f in "$HOME"/nav2*.log "$HOME"/eval*.txt; do [ -e "$f" ] && mv -- "$f" "$A/logs/"; done
[ -d "$HOME/.ros/log" ] && mv "$HOME/.ros/log" "$A/logs/ros_log"

# fresh params from stock Humble
python3 - "$A" <<'PY'
import sys, os, shutil, yaml
A = sys.argv[1]
stock = yaml.safe_load(open('/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml'))
good_p = A + '/params/nav2_limo.good.yaml'
CARRY = {'base_frame_id','odom_frame_id','global_frame_id','scan_topic','robot_base_frame','global_frame','odom_topic','map_topic','topic'}
carried = []
def walk(s, g, path):
    if not isinstance(s, dict) or not isinstance(g, dict): return
    for k, v in s.items():
        if k in CARRY and k in g and not isinstance(v, dict) and g[k] != v:
            carried.append((path + [k], v, g[k])); s[k] = g[k]
        elif k in g:
            walk(v, g[k], path + [k])
if os.path.exists(good_p):
    walk(stock, yaml.safe_load(open(good_p)), [])
a = stock['amcl']['ros__parameters']
a['set_initial_pose'] = True
a['initial_pose'] = {'x': -0.511, 'y': 0.300, 'z': 0.0, 'yaw': -1.527}
for n in ('local_costmap', 'global_costmap'):
    r = stock[n][n]['ros__parameters']
    r['robot_radius'] = 0.12
    if 'inflation_layer' in r:
        r['inflation_layer']['cost_scaling_factor'] = 5.0
        r['inflation_layer']['inflation_radius'] = 0.18
out = os.path.expanduser('~/limo_ws/params/nav2_limo.yaml')
yaml.safe_dump(stock, open(out, 'w'), sort_keys=False)
shutil.copy(out, os.path.expanduser('~/limo_ws/params/nav2_limo.baseline.yaml'))
print('carried over from good.yaml:')
for p, old, new in carried: print('  ', '.'.join(p), repr(old), '->', repr(new))
PY
echo "archive: $A"; ls -la "$P"
