#!/usr/bin/env bash
# setup_campus.sh - context8 Stages 0-3, AWS small-warehouse world.
# Run in WSL Ubuntu 22.04:  bash setup_campus.sh
# Re-runnable. Override the spawn with: SPAWN_X=.. SPAWN_Y=.. SPAWN_YAW=.. bash setup_campus.sh
set -eo pipefail
source /opt/ros/humble/setup.bash
source ~/limo_ws/install/setup.bash
WS=$HOME/limo_ws
SPAWN_X=${SPAWN_X:-0.0}; SPAWN_Y=${SPAWN_Y:-0.0}; SPAWN_YAW=${SPAWN_YAW:-0.0}   # UNVERIFIED guess; check at Gate 1

echo "== Stage 0: archive baseline =="
A=$WS/archive_2026-10-19
if [ ! -d "$A" ]; then
  mkdir -p "$A"
  cp -r $WS/params $WS/maps "$A"/ 2>/dev/null || true
  cp ~/*.py ~/sg.sh "$A"/ 2>/dev/null || true
fi

echo "== Stage 1: clone + build warehouse world =="
cd $WS/src
[ -d aws-robomaker-small-warehouse-world ] || \
  git clone -b ros2 https://github.com/aws-robotics/aws-robomaker-small-warehouse-world.git
cd $WS
rosdep install --from-paths src/aws-robomaker-small-warehouse-world --ignore-src -r -y || true
colcon build --symlink-install --packages-select aws_robomaker_small_warehouse_world
source install/setup.bash

WORLD=$(find $WS/src/aws-robomaker-small-warehouse-world/worlds -name 'small_warehouse.world' | head -1)
[ -n "$WORLD" ] || { echo "ERROR: small_warehouse.world not found"; ls -R $WS/src/aws-robomaker-small-warehouse-world/worlds; exit 1; }
echo "world: $WORLD"

cat > $WS/campus_env.sh <<EOF
# source this in T1 (and any terminal that runs gzclient) before launching Gazebo
export GAZEBO_MODEL_DATABASE_URI=""
R=$WS/src/aws-robomaker-small-warehouse-world
export GAZEBO_MODEL_PATH=\$R/models:\$R/fuel_models:$WS/src/limo_gazebosim/models:/usr/share/gazebo-11/models
EOF
echo "wrote $WS/campus_env.sh"

# Copy the Limo launch file; exact-string patch of world + spawn pose. Reports every hit count.
L=$WS/src/limo_gazebosim/launch
cp $L/limo_gazebo_diff.launch.py $L/limo_gazebo_warehouse.launch.py
WORLD="$WORLD" SPAWN_X=$SPAWN_X SPAWN_Y=$SPAWN_Y SPAWN_YAW=$SPAWN_YAW LAUNCH=$L/limo_gazebo_warehouse.launch.py python3 - <<'PY'
import os
p=os.environ['LAUNCH']; s=open(p).read()
subs=[('simulation_table.world',os.environ['WORLD']),
      ('-0.512',os.environ['SPAWN_X']),('0.297',os.environ['SPAWN_Y']),('-1.54',os.environ['SPAWN_YAW'])]
for old,new in subs:
    n=s.count(old); print(f"  patch {old!r} -> {new!r}: {n} occurrence(s)")
    if n==1: s=s.replace(old,new)
    else: print("  !! NOT patched (need manual edit, paste the grep below)")
open(p,'w').write(s)
PY
echo "-- relevant lines in limo_gazebo_warehouse.launch.py --"
grep -nE "world|spawn|'-x'|'-y'|'-Y'|-0\.512|0\.297|-1\.54" $L/limo_gazebo_warehouse.launch.py || true
echo "-- diff vs original --"
diff $L/limo_gazebo_diff.launch.py $L/limo_gazebo_warehouse.launch.py || true
cd $WS && colcon build --symlink-install --packages-select limo_gazebosim && source install/setup.bash
ros2 launch limo_gazebosim limo_gazebo_warehouse.launch.py --show-args | head -20 || true

echo "== Stage 2: gt_mapper2.py =="
cat > ~/gt_mapper2.py <<'PY'
#!/usr/bin/env python3
"""Ground-truth occupancy mapper: ray-casts /scan from tf odom->laser (odom == world, verified at spawn).
Usage: python3 ~/gt_mapper2.py --out ~/limo_ws/maps/campus_v1 --ros-args -p use_sim_time:=true
Drive with teleop (or explore_lite); Ctrl+C saves, autosave every 30 s. Output cropped to observed area."""
import argparse, math, sys
import numpy as np, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
import tf2_ros

ap = argparse.ArgumentParser()
ap.add_argument('--out', default='/root/campus_v1')
ap.add_argument('--res', type=float, default=0.05)
ap.add_argument('--x0', type=float, default=-30.0)   # grid lower-left, metres (world frame)
ap.add_argument('--y0', type=float, default=-30.0)
ap.add_argument('--size', type=float, default=60.0)  # grid side, metres
a, ros_args = ap.parse_known_args(sys.argv[1:])

class M(Node):
    def __init__(s):
        super().__init__('gt_mapper2', parameter_overrides=[])
        s.N = int(a.size / a.res)
        s.hit = np.zeros((s.N, s.N), np.int32); s.free = np.zeros((s.N, s.N), np.int32)
        s.buf = tf2_ros.Buffer(); s.tl = tf2_ros.TransformListener(s.buf, s)
        s.create_subscription(LaserScan, '/scan', s.cb, qos_profile_sensor_data)
        s.create_timer(30.0, s.save); s.n = 0
    def cell(s, x, y):
        return np.floor((y - a.y0) / a.res).astype(int), np.floor((x - a.x0) / a.res).astype(int)
    def cb(s, m):
        try:
            t = s.buf.lookup_transform('odom', m.header.frame_id, Time())
        except Exception:
            return
        q = t.transform.rotation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        px, py = t.transform.translation.x, t.transform.translation.y
        r = np.array(m.ranges, float); ang = yaw + m.angle_min + np.arange(len(r)) * m.angle_increment
        ok = ~np.isnan(r) & (r >= m.range_min)
        hitmask = ok & np.isfinite(r) & (r < m.range_max - 0.01)
        rr = np.where(np.isfinite(r), np.minimum(r, m.range_max), m.range_max)
        step = a.res * 0.5
        for i in np.where(ok)[0]:
            n = max(int(rr[i] / step), 1); d = np.linspace(0, rr[i], n, endpoint=False)
            iy, ix = s.cell(px + d*math.cos(ang[i]), py + d*math.sin(ang[i]))
            v = (iy >= 0) & (iy < s.N) & (ix >= 0) & (ix < s.N)
            s.free[iy[v], ix[v]] += 1
            if hitmask[i]:
                hy, hx = s.cell(np.array([px + rr[i]*math.cos(ang[i])]), np.array([py + rr[i]*math.sin(ang[i])]))
                if 0 <= hy[0] < s.N and 0 <= hx[0] < s.N: s.hit[hy[0], hx[0]] += 1
        s.n += 1
    def save(s):
        occ = (s.hit >= 3) & (s.hit >= 0.5 * s.free)
        fre = (s.free >= 1) & ~occ
        g = np.full((s.N, s.N), 205, np.uint8); g[fre] = 254; g[occ] = 0
        known = np.argwhere(g != 205)
        if len(known) == 0: return
        (y0, x0), (y1, x1) = known.min(0) - 10, known.max(0) + 10
        y0, x0 = max(y0, 0), max(x0, 0); y1, x1 = min(y1, s.N-1), min(x1, s.N-1)
        c = np.flipud(g[y0:y1+1, x0:x1+1])
        ox, oy = a.x0 + x0 * a.res, a.y0 + y0 * a.res
        with open(a.out + '.pgm', 'wb') as f:
            f.write(b'P5\n%d %d\n255\n' % (c.shape[1], c.shape[0])); f.write(c.tobytes())
        open(a.out + '.yaml', 'w').write(
            f"image: {a.out.split('/')[-1]}.pgm\nmode: trinary\nresolution: {a.res}\n"
            f"origin: [{ox:.3f}, {oy:.3f}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
        s.get_logger().info(f'saved {a.out}.pgm {c.shape[1]}x{c.shape[0]} px, scans={s.n}')

rclpy.init(args=ros_args); n = M()
try: rclpy.spin(n)
except KeyboardInterrupt: pass
n.save(); rclpy.shutdown()
PY
chmod +x ~/gt_mapper2.py

echo "== Stage 3: nav2_campus.yaml =="
mkdir -p $WS/params
[ -f $WS/params/nav2_campus.yaml ] && cp $WS/params/nav2_campus.yaml $WS/params/nav2_campus.yaml.prev
SPAWN_X=$SPAWN_X SPAWN_Y=$SPAWN_Y SPAWN_YAW=$SPAWN_YAW OUT=$WS/params/nav2_campus.yaml python3 - <<'PY'
import os, yaml
src = '/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml'
d = yaml.safe_load(open(src)); log = []
def P(path):
    o = d
    for k in path[:-1]:
        if not isinstance(o, dict) or k not in o: return None
        o = o[k]
    return o
def setk(path, val, delete=False):
    o = P(path); name = '/'.join(path)
    if o is None: log.append(f'MISSING PARENT {name}'); return
    if delete:
        if path[-1] in o: log.append(f'{name}: {o.pop(path[-1])} -> (removed)')
        return
    log.append(f'{name}: {o.get(path[-1], "<absent>")} -> {val}' + ('' if path[-1] in o else '  [ADDED]'))
    o[path[-1]] = val
RP = 'ros__parameters'
x, y, yaw = (float(os.environ[k]) for k in ('SPAWN_X', 'SPAWN_Y', 'SPAWN_YAW'))
# base frames
def frames(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('robot_base_frame', 'base_frame_id') and v != 'base_link': setk(path + [k], 'base_link')
            else: frames(v, path + [k])
frames(d, [])
a = ['amcl', RP]
setk(a + ['set_initial_pose'], True)
setk(a + ['initial_pose'], {'x': x, 'y': y, 'z': 0.0, 'yaw': yaw})
setk(a + ['transform_tolerance'], 1.0); setk(a + ['update_min_d'], 0.1); setk(a + ['update_min_a'], 0.15)
FP = '[[0.17,0.12],[0.17,-0.12],[-0.17,-0.12],[-0.17,0.12]]'
for cm in ('local_costmap', 'global_costmap'):
    b = [cm, cm, RP]
    setk(b + ['robot_radius'], None, delete=True); setk(b + ['footprint'], FP)
    setk(b + ['resolution'], 0.05)
    setk(b + ['inflation_layer', 'inflation_radius'], 0.45); setk(b + ['inflation_layer', 'cost_scaling_factor'], 3.0)
c = ['controller_server', RP]
setk(c + ['FollowPath', 'max_vel_x'], 0.3); setk(c + ['FollowPath', 'max_vel_theta'], 1.0)
setk(c + ['FollowPath', 'xy_goal_tolerance'], 0.15)
setk(c + ['general_goal_checker', 'xy_goal_tolerance'], 0.15); setk(c + ['general_goal_checker', 'yaw_goal_tolerance'], 0.5)
setk(c + ['progress_checker', 'required_movement_radius'], 0.1); setk(c + ['progress_checker', 'movement_time_allowance'], 15.0)
out = os.environ['OUT']
hdr = '# nav2_campus.yaml: stock Humble nav2_params.yaml + changes below (context8 Stage 3)\n' + ''.join(f'# CHANGE {l}\n' for l in log)
open(out, 'w').write(hdr + yaml.dump(d, sort_keys=False, default_flow_style=False))
print('\n'.join(log)); print('wrote', out)
PY

cat <<EOF

== DONE. Next (Gate 1) ==
T1: source /opt/ros/humble/setup.bash && source ~/limo_ws/install/setup.bash && source ~/limo_ws/campus_env.sh
    ros2 launch limo_gazebosim limo_gazebo_warehouse.launch.py headless:=True
T3: ros2 run teleop_twist_keyboard teleop_twist_keyboard   (then check /scan, drive every aisle)
Then map (T2): python3 ~/gt_mapper2.py --out ~/limo_ws/maps/campus_v1 --ros-args -p use_sim_time:=true
Paste back: this script's full output, plus 'ros2 topic list | head -30'.
EOF
