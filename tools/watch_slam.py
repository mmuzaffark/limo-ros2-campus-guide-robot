#!/usr/bin/env python3
import math, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid, Odometry

class W(Node):
    def __init__(s):
        super().__init__('watch_slam')
        s.pos = None; s.area = 0.0
        s.create_subscription(Odometry, '/odom', lambda m: setattr(s, 'pos', (m.pose.pose.position.x, m.pose.pose.position.y)), 10)
        q = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        s.create_subscription(OccupancyGrid, '/map', s.on_map, q)
    def on_map(s, m):
        known = sum(1 for v in m.data if v != -1)
        s.area = known * m.info.resolution ** 2

rclpy.init(); n = W(); hist = []; t0 = time.time(); last = 0
while rclpy.ok():
    rclpy.spin_once(n, timeout_sec=0.2)
    now = time.time()
    if now - last < 10 or n.pos is None: continue
    last = now; hist.append((now, n.pos, n.area))
    hist = [h for h in hist if now - h[0] <= 70]
    old = hist[0]
    moved = math.dist(n.pos, old[1]); grew = n.area - old[2]
    home = math.hypot(*n.pos) < 0.5; span = now - old[0]
    if span >= 55 and moved < 0.05 and grew < 0.5: st = 'DONE (at home, map stable)' if home else 'STUCK (no motion, no map growth)'
    elif moved < 0.05 and span >= 30: st = 'WAITING/ROTATING? (no motion 30 s+)'
    else: st = 'OK (moving)' if moved >= 0.05 else 'starting'
    print(f'[{int(now - t0):4d}s] pos ({n.pos[0]:6.2f},{n.pos[1]:6.2f})  moved {moved:4.2f} m/{span:.0f}s  '
          f'map {n.area:6.1f} m2 ({grew:+.1f})  -> {st}', flush=True)
