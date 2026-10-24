#!/usr/bin/env python3
import math, time, rclpy
from rclpy.node import Node
from rclpy.time import Time
from gazebo_msgs.msg import ModelStates
from tf2_ros import Buffer, TransformListener

class N(Node):
    def __init__(s):
        super().__init__('amcl_err2')
        s.buf = Buffer(); s.tl = TransformListener(s.buf, s)
        s.sub = s.create_subscription(ModelStates, '/gazebo/model_states', s.cb, 10)
        s.errs = []; s.prev = None; s.t0 = time.time(); s.last = 0
    def cb(s, m):
        idx = [i for i, n in enumerate(m.name) if 'limo' in n.lower()]
        if not idx: return
        p = m.pose[idx[0]].position
        try: t = s.buf.lookup_transform('map', 'base_link', Time()).transform.translation
        except Exception: return
        e = math.hypot(t.x - p.x, t.y - p.y)
        spd = 0.0 if s.prev is None else math.hypot(p.x - s.prev[0], p.y - s.prev[1]) / max(time.time() - s.prev[2], 1e-3)
        s.prev = (p.x, p.y, time.time()); s.errs.append((e, spd))
        if time.time() - s.last > 2:
            s.last = time.time()
            print(f'truth ({p.x:6.2f},{p.y:6.2f})  map-pose ({t.x:6.2f},{t.y:6.2f})  err {e:.3f} m  speed {spd:.2f} m/s', flush=True)

rclpy.init(); n = N()
try:
    while rclpy.ok() and time.time() - n.t0 < 300: rclpy.spin_once(n, timeout_sec=0.2)
except KeyboardInterrupt: pass
E = [e for e, _ in n.errs]; M = [e for e, v in n.errs if v > 0.1]; S = [e for e, v in n.errs if v <= 0.1]
f = lambda L: f'mean {sum(L)/len(L):.3f}  max {max(L):.3f}  (n={len(L)})' if L else 'no samples'
print('\nALL    ', f(E)); print('MOVING ', f(M)); print('STOPPED', f(S))
