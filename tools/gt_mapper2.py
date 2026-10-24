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
