#!/usr/bin/env python3
import math, os, sys, time, numpy as np, yaml, rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelStates
M = os.path.expanduser('~/limo_ws/maps/campus_slam')
y = yaml.safe_load(open(M + '.yaml')); res = y['resolution']; ox, oy = y['origin'][0], y['origin'][1]
raw = open(M + '.pgm', 'rb').read(); tok = []; i = 0
while len(tok) < 4:
    while raw[i:i+1].isspace(): i += 1
    if raw[i:i+1] == b'#':
        while raw[i:i+1] != b'\n': i += 1
        continue
    j = i
    while not raw[j:j+1].isspace(): j += 1
    tok.append(raw[i:j]); i = j
w, h = int(tok[1]), int(tok[2]); img = np.frombuffer(raw[i+1:], np.uint8)[:w*h].reshape(h, w)
r, c = np.nonzero(img == 0)
OCC = np.stack([ox + (c + 0.5) * res, oy + (h - 1 - r + 0.5) * res], 1)

class T(Node):
    def __init__(s):
        super().__init__('trace_goal'); s.pose = None; s.c1 = (0., 0.); s.c2 = (0., 0.); s.plan = None; s.np = 0
        s.create_subscription(ModelStates, '/gazebo/model_states', s.ms, 10)
        s.create_subscription(Twist, '/cmd_vel_nav', lambda m: setattr(s, 'c1', (m.linear.x, m.angular.z)), 10)
        s.create_subscription(Twist, '/cmd_vel', lambda m: setattr(s, 'c2', (m.linear.x, m.angular.z)), 10)
        s.create_subscription(Path, '/plan', s.pl, 10)
    def ms(s, m):
        k = [i for i, n in enumerate(m.name) if 'limo' in n.lower()]
        if k:
            p = m.pose[k[0]]; s.pose = (p.position.x, p.position.y, math.degrees(2 * math.atan2(p.orientation.z, p.orientation.w)))
    def pl(s, m):
        s.np += 1
        if s.np == 1 or s.np % 40 == 0: s.analyze(m)
        s.plan = m
    def analyze(s, m):
        P = np.array([[q.pose.position.x, q.pose.position.y] for q in m.poses])
        if len(P) < 2: return
        d = np.array([np.min(np.hypot(*(OCC - p).T)) for p in P])
        L = np.hstack([0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
        print(f'  PLAN #{s.np}: {len(P)} pts, {L[-1]:.1f} m, min wall clearance {d.min():.2f} m at ({P[d.argmin()][0]:.2f},{P[d.argmin()][1]:.2f})', flush=True)
        print('   path (x,y,clearance): ' + ' '.join(f'({P[k][0]:.1f},{P[k][1]:.1f},{d[k]:.2f})' for k in range(0, len(P), max(1, len(P) // 8))), flush=True)

T_END = float(sys.argv[1]) if len(sys.argv) > 1 else 60
rclpy.init(); n = T(); t0 = time.time(); last = 0
print('tracing; send the goal now with `go ...` in another terminal', flush=True)
while rclpy.ok() and time.time() - t0 < T_END:
    rclpy.spin_once(n, timeout_sec=0.2)
    if time.time() - last >= 2 and n.pose:
        last = time.time(); p = n.pose
        print(f'[{time.time()-t0:4.0f}s] pose ({p[0]:5.2f},{p[1]:5.2f}) yaw {p[2]:6.1f}  cmd_nav v={n.c1[0]:5.2f} w={n.c1[1]:5.2f}  cmd_vel v={n.c2[0]:5.2f} w={n.c2[1]:5.2f}', flush=True)
if n.plan: n.analyze(n.plan)
else: print('no /plan messages received', flush=True)
