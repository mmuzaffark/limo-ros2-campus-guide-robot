#!/usr/bin/env python3
import math, os, numpy as np, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from gazebo_msgs.msg import ModelStates
from tf2_ros import Buffer, TransformListener
from PIL import Image

RES, OX, OY, N = 0.05, -2.0, -2.0, 80
OUT = os.path.expanduser('~/limo_ws/maps/world_v2')
def yaw_of(q): return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
def line(c0, c1):
    (x0, y0), (x1, y1) = c0, c1
    dx, dy = abs(x1-x0), abs(y1-y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx-dy; out = []
    while (x0, y0) != (x1, y1):
        out.append((x0, y0)); e2 = 2*err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 < dx: err += dx; y0 += sy
    return out

class GT(Node):
    def __init__(self):
        super().__init__('gt_mapper', parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self.L = np.zeros((N, N)); self.pose = None; self.n = 0
        self.buf = Buffer(); TransformListener(self.buf, self)
        self.create_subscription(ModelStates, '/gazebo/model_states', self.on_ms, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(30.0, self.save)
    def on_ms(self, m):
        i = next((k for k, nm in enumerate(m.name) if 'limo' in nm), None)
        if i is not None:
            p = m.pose[i]; self.pose = (p.position.x, p.position.y, yaw_of(p.orientation))
    def cell(self, x, y): return int(math.floor((x-OX)/RES)), int(math.floor((y-OY)/RES))
    def ok(self, c): return 0 <= c[0] < N and 0 <= c[1] < N
    def on_scan(self, m):
        if self.pose is None: return
        try: t = self.buf.lookup_transform('base_link', m.header.frame_id, Time())
        except Exception: return
        lx, ly, lyaw = t.transform.translation.x, t.transform.translation.y, yaw_of(t.transform.rotation)
        bx, by, byaw = self.pose
        X = bx + lx*math.cos(byaw) - ly*math.sin(byaw); Y = by + lx*math.sin(byaw) + ly*math.cos(byaw)
        A = byaw + lyaw; c0 = self.cell(X, Y)
        for i, r in enumerate(m.ranges):
            if not (m.range_min < r < m.range_max): continue
            a = A + m.angle_min + i*m.angle_increment
            c1 = self.cell(X + r*math.cos(a), Y + r*math.sin(a))
            for c in line(c0, c1):
                if self.ok(c): self.L[c[1], c[0]] = max(self.L[c[1], c[0]] - 0.4, -4)
            if self.ok(c1): self.L[c1[1], c1[0]] = min(self.L[c1[1], c1[0]] + 0.85, 4)
        self.n += 1
    def save(self):
        img = np.full((N, N), 205, np.uint8); img[self.L < -0.4] = 254; img[self.L > 0.4] = 0
        img = img[::-1]
        Image.fromarray(img).save(OUT + '.pgm')
        Image.fromarray(img).resize((N*8, N*8), Image.NEAREST).save(OUT + '_preview.png')
        open(OUT + '.yaml', 'w').write(f'image: world_v2.pgm\nmode: trinary\nresolution: {RES}\norigin: [{OX}, {OY}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n')
        self.get_logger().info(f'saved: scans={self.n} occupied_cells={int((self.L > 0.4).sum())}')

rclpy.init(); n = GT()
try: rclpy.spin(n)
except KeyboardInterrupt: pass
n.save()
